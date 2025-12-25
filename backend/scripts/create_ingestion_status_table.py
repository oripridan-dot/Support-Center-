"""Create ingestion_status table for real-time tracking"""
from sqlmodel import Session, select
from app.core.database import engine
from app.models.ingestion_status import IngestionStatus
from app.models import Brand

def create_ingestion_status_table():
    """Create the ingestion_status table and initialize from brands"""
    from sqlmodel import SQLModel
    
    # Create table
    SQLModel.metadata.create_all(engine, tables=[IngestionStatus.__table__])
    print("✅ Created ingestion_status table")
    
    # Initialize status for all brands
    with Session(engine) as session:
        brands = session.exec(select(Brand)).all()
        
        for brand in brands:
            # Check if status exists
            existing = session.exec(
                select(IngestionStatus).where(IngestionStatus.brand_id == brand.id)
            ).first()
            
            if not existing:
                status = IngestionStatus(
                    brand_id=brand.id,
                    brand_name=brand.name,
                    status="idle",
                    progress_percent=0.0
                )
                session.add(status)
        
        session.commit()
        print(f"✅ Initialized status for {len(brands)} brands")

if __name__ == "__main__":
    create_ingestion_status_table()
