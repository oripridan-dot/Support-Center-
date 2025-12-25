"""Database model for ingestion status tracking"""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class IngestionStatus(SQLModel, table=True):
    """Real-time ingestion progress tracking in database"""
    __tablename__ = "ingestion_status"
    
    brand_id: int = Field(primary_key=True)
    brand_name: str
    status: str  # 'discovering', 'processing', 'complete', 'error'
    progress_percent: float = 0.0
    current_document: Optional[str] = None
    current_step: Optional[str] = None
    urls_discovered: int = 0
    urls_processed: int = 0
    documents_ingested: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    last_error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand_id": 1,
                "brand_name": "KRK Systems",
                "status": "processing",
                "progress_percent": 45.5,
                "current_document": "https://example.com/manual.pdf",
                "urls_discovered": 100,
                "urls_processed": 45
            }
        }
