import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func
from app.core.database import engine
from app.models.sql_models import Brand, Product, ProductFamily, Document

def list_missing():
    with Session(engine) as session:
        brand = session.exec(select(Brand).where(Brand.name == "Allen & Heath")).first()
        if not brand:
            print("Brand not found")
            return

        products = session.exec(
            select(Product)
            .join(ProductFamily)
            .where(ProductFamily.brand_id == brand.id)
        ).all()

        missing = []
        for product in products:
            docs = session.exec(select(Document).where(Document.product_id == product.id)).all()
            if not docs:
                missing.append(product)

        print(f"Found {len(missing)} products without documents:")
        for p in sorted(missing, key=lambda x: x.name):
            print(f"- {p.name} (ID: {p.id})")

if __name__ == "__main__":
    list_missing()
