from sqlmodel import Session, select
from backend.app.core.database import engine
from backend.app.models.sql_models import Product, Brand, ProductFamily, Document
import re

def normalize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def merge_duplicates():
    with Session(engine) as session:
        brand = session.exec(select(Brand).where(Brand.name == 'Allen & Heath')).first()
        products = session.exec(
            select(Product)
            .join(ProductFamily)
            .where(ProductFamily.brand_id == brand.id)
        ).all()
        
        normalized_map = {}
        to_delete = []
        
        for p in products:
            norm = normalize_name(p.name)
            if norm in normalized_map:
                existing = normalized_map[norm]
                print(f"Merging '{p.name}' (ID: {p.id}) into '{existing.name}' (ID: {existing.id})")
                
                # Move documents
                docs = session.exec(select(Document).where(Document.product_id == p.id)).all()
                for doc in docs:
                    doc.product_id = existing.id
                    session.add(doc)
                
                # If the duplicate has an image and the existing doesn't, move it
                if p.image_url and not existing.image_url:
                    existing.image_url = p.image_url
                    session.add(existing)
                
                to_delete.append(p)
            else:
                normalized_map[norm] = p
        
        session.commit()
        
        for p in to_delete:
            # Re-fetch to avoid session issues
            p_to_del = session.get(Product, p.id)
            if p_to_del:
                session.delete(p_to_del)
        
        session.commit()
        print(f"Successfully merged and deleted {len(to_delete)} duplicates.")

if __name__ == "__main__":
    merge_duplicates()
