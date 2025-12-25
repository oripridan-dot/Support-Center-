import sys
from pathlib import Path
from sqlmodel import Session, select, func

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand, Product, ProductFamily, Document

def check_presonus():
    with Session(engine) as session:
        # Check Brand
        brand = session.exec(select(Brand).where(Brand.name == "PreSonus")).first()
        if not brand:
            print("❌ Brand 'PreSonus' not found!")
            return
        
        print(f"✅ Brand found: {brand.name} (ID: {brand.id})")
        
        # Check Products
        products = session.exec(select(Product).join(ProductFamily).where(ProductFamily.brand_id == brand.id)).all()
        print(f"📊 Total Products: {len(products)}")
        
        if len(products) == 0:
            print("⚠️  No products found! This explains the 0% coverage.")
        else:
            for p in products[:5]:
                print(f"  - {p.name}")
        
        # Check Documents
        docs = session.exec(select(Document).where(Document.brand_id == brand.id)).all()
        print(f"📄 Total Documents: {len(docs)}")
        
        # Check Linked Documents
        linked_docs = [d for d in docs if d.product_id]
        print(f"🔗 Linked Documents: {len(linked_docs)}")
        
        if len(docs) > 0 and len(linked_docs) == 0:
            print("⚠️  Documents exist but none are linked to products.")

if __name__ == "__main__":
    check_presonus()
