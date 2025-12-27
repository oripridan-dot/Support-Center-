"""
Worker Status Tracker

Tracks real-time status of all 3 workers for UI display.
Provides clean, structured data about what each worker is currently doing.
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class WorkerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkerTask(BaseModel):
    """Current task being executed by a worker"""
    brand_id: int
    brand_name: str
    current_step: str
    progress: int  # 0-100
    total_items: int = 0
    completed_items: int = 0
    started_at: datetime
    estimated_completion: Optional[datetime] = None


class ExplorerStatus(BaseModel):
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[WorkerTask] = None
    last_completed: Optional[str] = None
    stats: Dict = {
        "brands_explored": 0,
        "total_docs_discovered": 0,
        "active_strategies": 0
    }


class ScraperStatus(BaseModel):
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[WorkerTask] = None
    last_completed: Optional[str] = None
    stats: Dict = {
        "docs_scraped_today": 0,
        "success_rate": 100.0,
        "failed_urls": 0
    }


class IngesterStatus(BaseModel):
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[WorkerTask] = None
    last_completed: Optional[str] = None
    stats: Dict = {
        "docs_ingested_today": 0,
        "chunks_created": 0,
        "avg_coverage": 0.0
    }


class WorkerStatusManager:
    """
    Singleton that tracks worker status for UI display
    """
    
    def __init__(self):
        self.explorer = ExplorerStatus()
        self.scraper = ScraperStatus()
        self.ingester = IngesterStatus()
        self.pipeline_logs: List[str] = []  # Recent activity log
    
    # Explorer methods
    def explorer_start(self, brand_id: int, brand_name: str, total_items: int = 0):
        self.explorer.status = WorkerStatus.RUNNING
        self.explorer.current_task = WorkerTask(
            brand_id=brand_id,
            brand_name=brand_name,
            current_step="Discovering documentation",
            progress=0,
            total_items=total_items,
            completed_items=0,
            started_at=datetime.now()
        )
        self._log(f"🔍 Explorer: Started discovering {brand_name} documentation")
    
    def explorer_progress(self, step: str, progress: int, completed: int = 0):
        if self.explorer.current_task:
            self.explorer.current_task.current_step = step
            self.explorer.current_task.progress = progress
            self.explorer.current_task.completed_items = completed
    
    def explorer_complete(self, docs_found: int):
        if self.explorer.current_task:
            brand_name = self.explorer.current_task.brand_name
            self.explorer.last_completed = f"{brand_name} ({docs_found} docs discovered)"
            self.explorer.stats["brands_explored"] += 1
            self.explorer.stats["total_docs_discovered"] += docs_found
            self._log(f"✅ Explorer: Completed {brand_name} - {docs_found} docs discovered")
        
        self.explorer.status = WorkerStatus.COMPLETED
        self.explorer.current_task = None
    
    def explorer_fail(self, error: str):
        self.explorer.status = WorkerStatus.FAILED
        self._log(f"❌ Explorer: Failed - {error}")
        self.explorer.current_task = None
    
    # Scraper methods
    def scraper_start(self, brand_id: int, brand_name: str, total_items: int):
        self.scraper.status = WorkerStatus.RUNNING
        self.scraper.current_task = WorkerTask(
            brand_id=brand_id,
            brand_name=brand_name,
            current_step="Collecting documents",
            progress=0,
            total_items=total_items,
            completed_items=0,
            started_at=datetime.now()
        )
        self._log(f"🤖 Scraper: Started scraping {brand_name} ({total_items} docs)")
    
    def scraper_progress(self, step: str, progress: int, completed: int):
        if self.scraper.current_task:
            self.scraper.current_task.current_step = step
            self.scraper.current_task.progress = progress
            self.scraper.current_task.completed_items = completed
    
    def scraper_complete(self, collected: int, failed: int = 0):
        if self.scraper.current_task:
            brand_name = self.scraper.current_task.brand_name
            self.scraper.last_completed = f"{brand_name} ({collected} docs collected)"
            self.scraper.stats["docs_scraped_today"] += collected
            self.scraper.stats["failed_urls"] += failed
            
            total = collected + failed
            success_rate = (collected / total * 100) if total > 0 else 100
            self.scraper.stats["success_rate"] = round(success_rate, 1)
            
            self._log(f"✅ Scraper: Completed {brand_name} - {collected}/{total} docs")
        
        self.scraper.status = WorkerStatus.COMPLETED
        self.scraper.current_task = None
    
    def scraper_fail(self, error: str):
        self.scraper.status = WorkerStatus.FAILED
        self._log(f"❌ Scraper: Failed - {error}")
        self.scraper.current_task = None
    
    # Ingester methods
    def ingester_start(self, brand_id: int, brand_name: str, total_items: int):
        self.ingester.status = WorkerStatus.RUNNING
        self.ingester.current_task = WorkerTask(
            brand_id=brand_id,
            brand_name=brand_name,
            current_step="Vectorizing documents",
            progress=0,
            total_items=total_items,
            completed_items=0,
            started_at=datetime.now()
        )
        self._log(f"📥 Ingester: Started indexing {brand_name} ({total_items} docs)")
    
    def ingester_progress(self, step: str, progress: int, completed: int, chunks: int = 0):
        if self.ingester.current_task:
            self.ingester.current_task.current_step = step
            self.ingester.current_task.progress = progress
            self.ingester.current_task.completed_items = completed
            if chunks > 0:
                self.ingester.stats["chunks_created"] = chunks
    
    def ingester_complete(self, ingested: int, chunks: int, coverage: float):
        if self.ingester.current_task:
            brand_name = self.ingester.current_task.brand_name
            self.ingester.last_completed = f"{brand_name} ({coverage}% coverage)"
            self.ingester.stats["docs_ingested_today"] += ingested
            self.ingester.stats["chunks_created"] += chunks
            
            # Update average coverage
            brands = self.explorer.stats["brands_explored"]
            if brands > 0:
                current_avg = self.ingester.stats["avg_coverage"]
                self.ingester.stats["avg_coverage"] = round(
                    (current_avg * (brands - 1) + coverage) / brands, 1
                )
            
            self._log(f"✅ Ingester: Completed {brand_name} - {coverage}% coverage")
        
        self.ingester.status = WorkerStatus.COMPLETED
        self.ingester.current_task = None
    
    def ingester_fail(self, error: str):
        self.ingester.status = WorkerStatus.FAILED
        self._log(f"❌ Ingester: Failed - {error}")
        self.ingester.current_task = None
    
    def _log(self, message: str):
        """Add to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.pipeline_logs.append(f"[{timestamp}] {message}")
        # Keep only last 50 logs
        if len(self.pipeline_logs) > 50:
            self.pipeline_logs = self.pipeline_logs[-50:]
    
    def get_status(self) -> Dict:
        """Get complete status for UI"""
        return {
            "explorer": self.explorer.model_dump(),
            "scraper": self.scraper.model_dump(),
            "ingester": self.ingester.model_dump(),
            "recent_activity": self.pipeline_logs[-10:],  # Last 10 activities
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """Reset daily stats (call at midnight)"""
        self.scraper.stats["docs_scraped_today"] = 0
        self.ingester.stats["docs_ingested_today"] = 0
        self.ingester.stats["chunks_created"] = 0
        self.pipeline_logs = []


# Global singleton
worker_status = WorkerStatusManager()
