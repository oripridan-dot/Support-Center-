from sqlmodel import Session, select, func
from app.core.database import engine
from app.models.sql_models import Brand, Document

def check_status():
    with Session(engine) as session:
        brands = session.exec(select(Brand)).all()
        print(f"{'ID':<5} {'Brand':<20} {'Docs':<10} {'Status'}")
        print("-" * 50)
        
        for brand in brands:
            doc_count = session.exec(select(func.count(Document.id)).where(Document.brand_id == brand.id)).one()
            status = "✅ OK" if doc_count > 0 else "❌ Needs Attention"
            print(f"{brand.id:<5} {brand.name:<20} {doc_count:<10} {status}")

if __name__ == "__main__":
    check_status()
