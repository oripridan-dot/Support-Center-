"""
Real-time ingestion status endpoints with WebSocket support
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
from pathlib import Path
from app.services.ingestion_tracker import tracker, INGESTION_STATUS_FILE

router = APIRouter()

class IngestionStatus(BaseModel):
    is_running: bool
    current_brand: Optional[str] = None
    current_step: Optional[str] = None
    total_documents: int = 0
    documents_by_brand: dict = {}
    urls_discovered: int = 0
    urls_processed: int = 0
    progress_percent: float = 0.0
    last_updated: str = ""
    errors: list = []
    start_time: Optional[str] = None
    estimated_completion: Optional[str] = None
    brand_progress: dict = {}

def get_ingestion_status() -> dict:
    """Read current ingestion status from file or tracker"""
    try:
        if Path(INGESTION_STATUS_FILE).exists():
            with open(INGESTION_STATUS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    return tracker.status

@router.get("/status", response_model=IngestionStatus)
async def get_status():
    """Get current ingestion status"""
    status = get_ingestion_status()
    return IngestionStatus(**status)

@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket endpoint for real-time ingestion updates"""
    await websocket.accept()
    last_update = None
    
    try:
        while True:
            # Read current status from file
            try:
                if Path(INGESTION_STATUS_FILE).exists():
                    with open(INGESTION_STATUS_FILE, 'r') as f:
                        current_status = json.load(f)
                        
                        # Only send if status changed
                        if current_status != last_update:
                            last_update = current_status.copy()
                            await websocket.send_json(current_status)
            except Exception as e:
                await websocket.send_json({"error": str(e)})
            
            # Check every 500ms for updates
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

@router.post("/reset")
async def reset_ingestion():
    """Reset ingestion tracker"""
    tracker.reset()
    return {"message": "Ingestion tracker reset"}

@router.get("/stats")
async def get_stats():
    """Get ingestion statistics"""
    status = get_ingestion_status()
    
    return {
        "total_documents": status.get("total_documents", 0),
        "documents_by_brand": status.get("documents_by_brand", {}),
        "is_running": status.get("is_running", False),
        "progress_percent": status.get("progress_percent", 0),
        "errors_count": len(status.get("errors", [])),
        "brand_count": len(status.get("documents_by_brand", {}))
    }
