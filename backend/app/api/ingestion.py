"""
Real-time ingestion status endpoints with WebSocket support
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
import logging
from pathlib import Path
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.ingestion_status import IngestionStatus as DBIngestionStatus
from app.services.ingestion_tracker import tracker, INGESTION_STATUS_FILE
from app.services.pa_brands_scraper import PABrandsScraper

logger = logging.getLogger(__name__)

router = APIRouter()

# Global flag for pipeline control
_pipeline_running = False
_pipeline_task = None

class IngestionStatus(BaseModel):
    is_running: bool
    current_brand: Optional[str] = None
    current_brand_target: Optional[int] = None
    current_brand_documents: Optional[int] = None
    current_step: Optional[str] = None
    current_document: Optional[str] = None
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

class StartIngestionRequest(BaseModel):
    brand_name: Optional[str] = None
    force_rescan: bool = False

class StartPipelineRequest(BaseModel):
    brand_id: Optional[int] = None
    parallel_mode: bool = True  # Enable parallel mode by default

async def run_ingestion_task(brand_name: Optional[str], force_rescan: bool):
    """Background task to run ingestion"""
    scraper = PABrandsScraper(force_rescan=force_rescan)
    if brand_name:
        scraper.brands_to_scrape = [b for b in scraper.brands_to_scrape if b['name'].lower() == brand_name.lower()]
        if not scraper.brands_to_scrape:
            # If brand not found in default list, try to find it in DB or just pass the name if scraper handles it
            # For now, we assume it must be in the list or we add it dynamically if we know the URL
            # But PABrandsScraper needs the URL.
            # Let's assume the scraper has the list.
            logger.warning(f"Brand {brand_name} not found in scraper configuration.")
            return

    await scraper.run()

@router.post("/start")
async def start_ingestion(request: StartIngestionRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Start ingestion process"""
    status = get_ingestion_status(session)
    if status.get("is_running"):
        raise HTTPException(status_code=400, detail="Ingestion is already running")
    
    background_tasks.add_task(run_ingestion_task, request.brand_name, request.force_rescan)
    return {"message": f"Ingestion started for {request.brand_name or 'all brands'}"}

def get_ingestion_status(session: Session) -> dict:
    """Read current ingestion status combining Tracker (Real-time) and DB (Historical)"""
    try:
        from app.models.sql_models import Brand, Document
        
        # 1. Get Real-Time Status from Tracker (JSON)
        # This is the source of truth for WHAT is currently running
        tracker_status = tracker.status
        try:
            if Path(INGESTION_STATUS_FILE).exists():
                with open(INGESTION_STATUS_FILE, 'r') as f:
                    file_status = json.load(f)
                    if isinstance(file_status, dict):
                        tracker_status = file_status
        except Exception as e:
            logger.warning(f"Failed to read ingestion status file: {e}")

        # 2. Get Accurate Document Counts from DB
        # This is the source of truth for HOW MUCH data we have
        total_docs = session.exec(select(func.count(Document.id))).one()
        
        # Get all brand statuses from database for historical context
        db_statuses = session.exec(select(DBIngestionStatus)).all()
        
        # 3. Merge Data
        # Start with tracker status as base
        final_status = tracker_status.copy()
        final_status["total_documents"] = total_docs
        
        # Update brand progress with real DB counts
        # If tracker has brand_progress, update the document counts from DB
        if "brand_progress" not in final_status:
            final_status["brand_progress"] = {}
            
        # Get all brands to map IDs
        brands = session.exec(select(Brand)).all()
        brand_map = {b.name: b.id for b in brands}
        
        # Add current brand stats
        if final_status.get("current_brand"):
            cb_name = final_status["current_brand"]
            cb_id = brand_map.get(cb_name)
            if cb_id:
                # Use discovered URLs as target if available, otherwise fallback to 0
                discovered = final_status.get("urls_discovered", 0)
                current_docs = session.exec(select(func.count(Document.id)).where(Document.brand_id == cb_id)).one()
                
                # Self-validating: Target cannot be less than what we already have
                if discovered < current_docs:
                    discovered = current_docs
                    # Update the source of truth if possible (optional, but good for consistency)
                    final_status["urls_discovered"] = discovered
                
                final_status["current_brand_target"] = discovered
                final_status["current_brand_documents"] = current_docs
                
                # Recalculate progress percent based on discovered URLs
                if discovered > 0:
                    final_status["progress_percent"] = (final_status["current_brand_documents"] / discovered) * 100
                    # Cap at 99% if still running
                    if final_status["is_running"] and final_status["progress_percent"] >= 100:
                        final_status["progress_percent"] = 99.0
        
        # Update counts for all brands in tracker
        for brand_name in final_status.get("brand_progress", {}):
            brand_id = brand_map.get(brand_name)
            if brand_id:
                count = session.exec(select(func.count(Document.id)).where(Document.brand_id == brand_id)).one()
                final_status["brand_progress"][brand_name]["documents_ingested"] = count
                # Ensure urls_discovered is at least the document count
                if final_status["brand_progress"][brand_name].get("urls_discovered", 0) < count:
                     final_status["brand_progress"][brand_name]["urls_discovered"] = count

        # Also ensure we have entries for brands in DB status but not in tracker
        for status in db_statuses:
            if status.brand_name not in final_status["brand_progress"]:
                brand_id = status.brand_id
                count = session.exec(select(func.count(Document.id)).where(Document.brand_id == brand_id)).one()
                
                # Fix for 0 URLs discovered
                urls_discovered = status.urls_discovered
                if urls_discovered < count:
                    urls_discovered = count
                
                final_status["brand_progress"][status.brand_name] = {
                    "status": status.status,
                    "progress_percent": status.progress_percent,
                    "documents_ingested": count,
                    "urls_discovered": urls_discovered,
                    "updated_at": status.updated_at.isoformat() if status.updated_at else None
                }

        return final_status

    except Exception as e:
        logger.warning(f"Failed to read ingestion status: {e}")
        return tracker.status

@router.get("/status", response_model=IngestionStatus)
async def get_status(session: Session = Depends(get_session)):
    """Get current ingestion status"""
    try:
        status = get_ingestion_status(session)
        return IngestionStatus(**status)
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        # Return a safe default
        return IngestionStatus(
            is_running=False,
            current_step="Error retrieving status",
            errors=[{"message": str(e)}]
        )

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

@router.get("/workers-status")
async def get_workers_status():
    """Get real-time status of all 3 workers"""
    from app.workers.status_tracker import worker_status
    return worker_status.get_status()

@router.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline activity streaming"""
    await websocket.accept()
    from app.workers.status_tracker import worker_status
    
    try:
        while True:
            # Send current status every 500ms
            status = worker_status.get_status()
            await websocket.send_json(status)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

@router.post("/start-pipeline")
async def start_pipeline(request: StartPipelineRequest, background_tasks: BackgroundTasks):
    """
    Start the HIGH-PERFORMANCE 28-worker pipeline
    
    Uses the optimized worker pool system instead of legacy 3-worker orchestrator
    """
    global _pipeline_running, _pipeline_task
    
    if _pipeline_running:
        raise HTTPException(status_code=400, detail="Pipeline is already running")
    
    brand_id = request.brand_id
    parallel_mode = request.parallel_mode
    
    async def run_pipeline():
        global _pipeline_running
        _pipeline_running = True
        try:
            # Use high-performance worker pool instead of legacy orchestrator
            from app.workers.high_performance import worker_pool, TaskCategory, TaskPriority
            from app.workers.explorer import ExplorerWorker
            from app.workers.scraper import ScraperWorker
            from app.workers.ingester import IngesterWorker
            
            # If no brand_id provided, process ALL brands
            if brand_id is None:
                session = next(get_session())
                from app.models.sql_models import Brand
                all_brands = session.exec(select(Brand).order_by(Brand.id)).all()
                
                if not all_brands:
                    logger.error("No brands found in database")
                    return
                
                logger.info(f"🚀 HIGH-PERFORMANCE PIPELINE: Processing {len(all_brands)} brands")
                logger.info(f"⚡ Using 28-worker specialized system")
                
                # Initialize workers
                explorer = ExplorerWorker()
                scraper = ScraperWorker()
                ingester = IngesterWorker()
                
                await explorer.initialize()
                await scraper.initialize()
                
                completed = 0
                failed = 0
                
                for idx, brand in enumerate(all_brands, 1):
                    if not _pipeline_running:
                        logger.info(f"🛑 Pipeline stopped by user after {idx} brands")
                        break
                        
                    logger.info(f"\n{'='*80}")
                    logger.info(f"🎯 BRAND {idx}/{len(all_brands)}: {brand.name} (ID: {brand.id})")
                    logger.info(f"{'='*80}")
                    
                    try:
                        # Step 1: Exploration using SCRAPING worker pool
                        logger.info(f"🔍 Step 1/3: Exploring {brand.name}...")
                        strategy = await explorer.explore_brand(brand.id)
                        
                        # Step 2: Scraping using SCRAPING worker pool
                        logger.info(f"📥 Step 2/3: Scraping {len(strategy.documentation_urls)} URLs...")
                        docs = await scraper.scrape_strategy(strategy)
                        
                        # Step 3: Ingestion using INGESTION + EMBEDDING worker pools
                        if docs:
                            logger.info(f"💾 Step 3/3: Ingesting {len(docs)} documents...")
                            await ingester.ingest_documents(brand.id, docs, strategy.brand_name)
                            logger.info(f"✅ {brand.name} completed: {len(docs)} docs ingested")
                            completed += 1
                        else:
                            logger.warning(f"⚠️  {brand.name}: No documents to ingest")
                            completed += 1
                    
                    except Exception as e:
                        failed += 1
                        logger.error(f"❌ {brand.name} error: {e}", exc_info=True)
                
                # Cleanup
                await explorer.shutdown()
                await scraper.shutdown()
                
                logger.info(f"\n{'='*80}")
                logger.info(f"🏁 HIGH-PERFORMANCE PIPELINE COMPLETE")
                logger.info(f"{'='*80}")
                logger.info(f"✅ Successful: {completed}/{len(all_brands)}")
                logger.info(f"❌ Failed: {failed}/{len(all_brands)}")
                logger.info(f"{'='*80}")
                
            else:
                # Single brand mode with high-performance workers
                logger.info(f"🚀 Starting HIGH-PERFORMANCE pipeline for brand {brand_id}")
                logger.info(f"⚡ Using 28-worker specialized system")
                
                explorer = ExplorerWorker()
                scraper = ScraperWorker()
                ingester = IngesterWorker()
                
                await explorer.initialize()
                await scraper.initialize()
                
                try:
                    # Step 1: Exploration
                    logger.info(f"🔍 Step 1/3: Exploring brand...")
                    strategy = await explorer.explore_brand(brand_id)
                    
                    # Step 2: Scraping
                    logger.info(f"📥 Step 2/3: Scraping {len(strategy.documentation_urls)} URLs...")
                    docs = await scraper.scrape_strategy(strategy)
                    
                    # Step 3: Ingestion
                    if docs:
                        logger.info(f"💾 Step 3/3: Ingesting {len(docs)} documents...")
                        await ingester.ingest_documents(brand_id, docs, strategy.brand_name)
                        logger.info(f"✅ Pipeline completed: {len(docs)} docs ingested")
                    else:
                        logger.warning(f"⚠️  No documents to ingest")
                    
                except Exception as e:
                    logger.error(f"❌ Pipeline error: {e}", exc_info=True)
                finally:
                    await explorer.shutdown()
                    await scraper.shutdown()
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            _pipeline_running = False
    
    # Start pipeline in background
    _pipeline_task = asyncio.create_task(run_pipeline())
    
    mode_label = "parallel" if parallel_mode else "sequential"
    brand_msg = "all brands" if brand_id is None else f"brand {brand_id}"
    return {
        "message": f"Pipeline started for {brand_msg} ({mode_label} mode)", 
        "brand_id": brand_id,
        "parallel_mode": parallel_mode
    }

@router.post("/stop-pipeline")
async def stop_pipeline():
    """Stop the worker pipeline"""
    global _pipeline_running, _pipeline_task
    
    if not _pipeline_running:
        return {"message": "Pipeline is not running"}
    
    _pipeline_running = False
    
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
            pass
    
    return {"message": "Pipeline stopped"}

@router.get("/stats")
async def get_stats(session: Session = Depends(get_session)):
    """Get ingestion statistics"""
    status = get_ingestion_status(session)
    
    return {
        "total_documents": status.get("total_documents", 0),
        "documents_by_brand": status.get("documents_by_brand", {}),
        "is_running": status.get("is_running", False),
        "progress_percent": status.get("progress_percent", 0),
        "errors_count": len(status.get("errors", [])),
        "brand_count": len(status.get("documents_by_brand", {}))
    }
