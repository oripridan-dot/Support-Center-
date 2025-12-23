from sqlmodel import Session, select
from backend.app.core.database import engine
from backend.app.models.sql_models import Product, Brand, ProductFamily
import re

def normalize_name(name):
    # Remove non-alphanumeric and lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def find_duplicates():
    with Session(engine) as session:
        brand = session.exec(select(Brand).where(Brand.name == 'Allen & Heath')).first()
        products = session.exec(
            select(Product)
            .join(ProductFamily)
            .where(ProductFamily.brand_id == brand.id)
        ).all()
        
        normalized_map = {}
        duplicates = []
        
        for p in products:
            norm = normalize_name(p.name)
            if norm in normalized_map:
                duplicates.append((normalized_map[norm], p))
            else:
                normalized_map[norm] = p
                
        print(f"Found {len(duplicates)} potential duplicate pairs.")
        for p1, p2 in duplicates:
            print(f"  '{p1.name}' (ID: {p1.id}) <-> '{p2.name}' (ID: {p2.id})")

if __name__ == "__main__":
    find_duplicates()
