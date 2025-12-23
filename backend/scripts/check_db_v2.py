import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func
from app.core.database import engine
from app.models.sql_models import Brand, Product, ProductFamily, Document

def check():
    with Session(engine) as session:
        brands = session.exec(select(Brand)).all()
        for brand in brands:
            total = session.exec(
                select(func.count(Product.id))
                .join(ProductFamily)
                .where(ProductFamily.brand_id == brand.id)
            ).one()
            covered = session.exec(
                select(func.count(func.distinct(Product.id)))
                .join(ProductFamily)
                .join(Document, Product.id == Document.product_id)
                .where(ProductFamily.brand_id == brand.id)
            ).one()
            print(f"Brand: {brand.name}")
            print(f"  Total Products: {total}")
            print(f"  Covered Products: {covered}")
            print(f"  Coverage: {covered/total*100 if total > 0 else 0:.1f}%")

if __name__ == "__main__":
    check()
