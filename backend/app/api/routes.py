from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.llm import llm_service
from app.services.vector_db import vector_db

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

@router.post("/search", response_model=SearchResponse)
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

@router.get("/health")
async def health():
    return {"status": "ok"}
