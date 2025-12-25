"""
Documents API - Real-time document feed
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_session
from app.models.sql_models import Document, Brand
from pydantic import BaseModel

router = APIRouter()

class DocumentItem(BaseModel):
    id: int
    title: str
    url: Optional[str]
    brand_name: str
    brand_id: int
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class RecentDocumentsResponse(BaseModel):
    total: int
    documents: List[DocumentItem]
    last_updated: datetime

@router.get("/recent", response_model=RecentDocumentsResponse)
def get_recent_documents(
    limit: int = Query(default=20, le=100),
    brand_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Get recently added/updated documents"""
    
    # Build query
    query = (
        select(Document, Brand.name.label('brand_name'))
        .join(Brand, Document.brand_id == Brand.id)
        .order_by(Document.id.desc())  # Most recent by ID (insertion order)
    )
    
    if brand_id:
        query = query.where(Document.brand_id == brand_id)
    
    query = query.limit(limit)
    
    # Execute query
    results = session.exec(query).all()
    
    documents = [
        DocumentItem(
            id=doc.id,
            title=doc.title or "Untitled",
            url=doc.url,
            brand_name=brand_name,
            brand_id=doc.brand_id,
            updated_at=datetime.now()  # Use current time as proxy
        )
        for doc, brand_name in results
    ]
    
    # Get total count
    total_query = select(func.count(Document.id))
    if brand_id:
        total_query = total_query.where(Document.brand_id == brand_id)
    total = session.exec(total_query).one()
    
    return RecentDocumentsResponse(
        total=total,
        documents=documents,
        last_updated=datetime.now()
    )

@router.get("/stats")
def get_document_stats(session: Session = Depends(get_session)):
    """Get global document statistics"""
    
    total_docs = session.exec(select(func.count(Document.id))).one()
    
    # Docs per brand
    brand_stats = session.exec(
        select(
            Brand.name,
            func.count(Document.id).label('doc_count')
        )
        .join(Document, Brand.id == Document.brand_id, isouter=True)
        .group_by(Brand.name)
        .order_by(func.count(Document.id).desc())
    ).all()
    
    return {
        "total_documents": total_docs,
        "brands_with_docs": len([b for b in brand_stats if b[1] > 0]),
        "top_brands": [
            {"name": name, "doc_count": count}
            for name, count in brand_stats[:10]
        ]
    }
