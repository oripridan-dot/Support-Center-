from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.llm import llm_service
from app.services.vector_db import vector_db
from datetime import datetime

# Import sub-routers
from .brands import router as brands_router
from .chat import router as chat_router
from .documents import router as documents_router
from .async_endpoints import router as async_router
# Legacy ingestion and workers routers removed - using HP 22-worker system only

router = APIRouter()

# Include sub-routers (removed legacy ingestion and workers)
router.include_router(brands_router, prefix="/brands", tags=["brands"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(async_router, prefix="/v2", tags=["async", "performance"])

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

# --- Search Endpoints ---
@router.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        # 1. Get embedding for query
        query_embedding = llm_service.get_embedding(request.query)
        
        # 2. Search vector DB
        search_results = vector_db.search(
            query_vector=query_embedding,
            limit=5,
            filter_criteria=request.filters
        )
        
        # 3. Construct context
        context = ""
        sources = []
        for result in search_results:
            context += f"Source ({result.payload.get('brand')} - {result.payload.get('product_model')}): {result.payload.get('text')}\n\n"
            sources.append(result.payload)
            
        # 4. Generate answer
        answer = llm_service.generate_response(request.query, context)
        
        return SearchResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/health")
async def health():
    return {"status": "ok"}

# --- Ingestion Endpoints (Mock for Frontend Compatibility) ---

class IngestionStatus(BaseModel):
    is_running: bool
    current_brand: Optional[str]
    current_step: Optional[str]
    current_document: Optional[str]
    total_documents: int
    current_brand_documents: Optional[int]
    current_brand_target: Optional[int]
    current_brand_progress: Optional[int]
    documents_by_brand: Dict[str, int]
    urls_discovered: int
    urls_processed: int
    progress_percent: int
    last_updated: str
    errors: List[Dict[str, str]]
    start_time: Optional[str]
    estimated_completion: Optional[str]
    brand_progress: Dict[str, Any]

@router.get("/ingestion/status", response_model=IngestionStatus)
async def get_ingestion_status():
    return IngestionStatus(
        is_running=False,
        current_brand=None,
        current_step=None,
        current_document=None,
        total_documents=0,
        current_brand_documents=0,
        current_brand_target=0,
        current_brand_progress=0,
        documents_by_brand={},
        urls_discovered=0,
        urls_processed=0,
        progress_percent=0,
        last_updated=datetime.now().isoformat(),
        errors=[],
        start_time=None,
        estimated_completion=None,
        brand_progress={}
    )

@router.post("/ingestion/start")
async def start_ingestion():
    return {"message": "Ingestion started (mock)"}
