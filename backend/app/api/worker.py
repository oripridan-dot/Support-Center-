"""Worker control API endpoints"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import subprocess
import signal
import os

router = APIRouter(tags=["worker"])

# Track worker process
worker_process = None

class WorkerStartRequest(BaseModel):
    mode: str = "once"  # "once" or "continuous"
    brand_name: Optional[str] = None
    delay: int = 60

class WorkerStatusResponse(BaseModel):
    is_running: bool
    pid: Optional[int] = None
    mode: Optional[str] = None

@router.post("/start")
async def start_worker(request: WorkerStartRequest):
    """Start the scraper worker"""
    global worker_process
    
    if worker_process and worker_process.poll() is None:
        return {"status": "already_running", "pid": worker_process.pid}
    
    # Build command
    cmd = ["python", "worker.py", "--mode", request.mode]
    
    if request.brand_name:
        cmd.extend(["--brand", request.brand_name])
    
    if request.mode == "continuous":
        cmd.extend(["--delay", str(request.delay)])
    
    # Start worker process
    worker_process = subprocess.Popen(
        cmd,
        cwd="/workspaces/Support-Center-/backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    return {
        "status": "started",
        "pid": worker_process.pid,
        "mode": request.mode,
        "brand": request.brand_name
    }

@router.post("/stop")
async def stop_worker():
    """Stop the scraper worker"""
    global worker_process
    
    if not worker_process or worker_process.poll() is not None:
        return {"status": "not_running"}
    
    # Send SIGTERM for graceful shutdown
    worker_process.terminate()
    
    try:
        worker_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        # Force kill if it doesn't stop
        worker_process.kill()
    
    return {"status": "stopped"}

@router.get("/status", response_model=WorkerStatusResponse)
async def worker_status():
    """Get worker status"""
    global worker_process
    
    if worker_process and worker_process.poll() is None:
        return WorkerStatusResponse(
            is_running=True,
            pid=worker_process.pid
        )
    
    return WorkerStatusResponse(is_running=False)

@router.post("/scrape/{brand_name}")
async def scrape_brand(brand_name: str, background_tasks: BackgroundTasks):
    """Trigger scraping for a specific brand (runs once)"""
    
    def run_scrape():
        subprocess.run(
            ["python", "worker.py", "--mode", "once", "--brand", brand_name],
            cwd="/workspaces/Support-Center-/backend"
        )
    
    background_tasks.add_task(run_scrape)
    
    return {
        "status": "scheduled",
        "brand": brand_name,
        "message": f"Scraping job queued for {brand_name}"
    }
