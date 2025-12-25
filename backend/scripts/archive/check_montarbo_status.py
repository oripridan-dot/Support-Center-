
from app.core.database import get_session
from app.models.sql_models import Brand, Product, Document
from sqlmodel import select

with next(get_session()) as db:
    brand = db.exec(select(Brand).where(Brand.name == "Montarbo")).first()
    if brand:
        print(f"Brand: {brand.name} (ID: {brand.id})")
        products = db.exec(select(Product).where(Product.family_id.in_(
            select(Product.family_id).where(Product.family_id != None) # Simplified check
        ))).all()
        
        # Count products for this brand
        # We need to join with ProductFamily to be precise, but let's just count docs for now
        docs = db.exec(select(Document).where(Document.brand_id == brand.id)).all()
        print(f"Documents: {len(docs)}")
        for doc in docs[:5]:
            print(f" - {doc.title} ({doc.url})")
    else:
        print("Montarbo brand not found")
