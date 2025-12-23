import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand, Product, Document

def fix_missing():
    mapping = {
        # ZED Series
        "ZED-6": "https://www.allen-heath.com/hardware/zed-series/zed-mini/",
        "ZED-6 FX": "https://www.allen-heath.com/hardware/zed-series/zed-mini/",
        "ZED-10": "https://www.allen-heath.com/hardware/zed-series/zed-compact/",
        "ZED-10FX": "https://www.allen-heath.com/hardware/zed-series/zed-compact/",
        "ZED60-10FX": "https://www.allen-heath.com/hardware/zed-series/zed-compact/",
        "ZED60-14FX": "https://www.allen-heath.com/hardware/zed-series/zed-compact/",
        "ZED-12FX": "https://www.allen-heath.com/hardware/zed-series/zed-mid/",
        "ZED-14": "https://www.allen-heath.com/hardware/zed-series/zed-mid/",
        "ZED-16FX": "https://www.allen-heath.com/hardware/zed-series/zed-mid/",
        "ZED-22FX": "https://www.allen-heath.com/hardware/zed-series/zed-mid/",
        "ZED-428": "https://www.allen-heath.com/hardware/zed-series/zed-max/",
        "ZEDi-8": "https://www.allen-heath.com/hardware/zed-series/zedi-compact/",
        "ZEDi-10": "https://www.allen-heath.com/hardware/zed-series/zedi-compact/",
        "ZEDi-10 FX": "https://www.allen-heath.com/hardware/zed-series/zedi-compact/",
        
        # Xone Series
        "Xone:92 MK2": "https://www.allen-heath.com/hardware/xone-series/xone92/",
        "Xone24": "https://www.allen-heath.com/hardware/xone-series/xone24/",
        "Xone24C": "https://www.allen-heath.com/hardware/xone-series/xone24c/",
        "Xone43": "https://www.allen-heath.com/hardware/xone-series/xone43/",
        "Xone92": "https://www.allen-heath.com/hardware/xone-series/xone92/",
        "Xone92 Limited Edition": "https://www.allen-heath.com/hardware/xone-series/xone92-limited-edition/",
        "Xone96": "https://www.allen-heath.com/hardware/xone-series/xone96/",
        "Xonek3": "https://www.allen-heath.com/hardware/xone-series/xonek3/",
        "Xonepx5": "https://www.allen-heath.com/hardware/xone-series/xonepx5/",
        
        # Qu Series
        "QU-5": "https://www.allen-heath.com/hardware/qu/qu-5-qu-5d/",
        "QU-5D": "https://www.allen-heath.com/hardware/qu/qu-5-qu-5d/",
        "QU-6": "https://www.allen-heath.com/hardware/qu/qu-6-qu-6d/",
        "QU-6D": "https://www.allen-heath.com/hardware/qu/qu-6-qu-6d/",
        "QU-7": "https://www.allen-heath.com/hardware/qu/qu-7-qu-7d/",
        "QU-7D": "https://www.allen-heath.com/hardware/qu/qu-7-qu-7d/",
        "Qu-32 Chrome": "https://www.allen-heath.com/hardware/qu/qu-classic/",
        
        # Others
        "DX168/X": "https://www.allen-heath.com/hardware/everything-i-o/dx168/",
        "Ab168": "https://www.allen-heath.com/hardware/everything-i-o/ab168/",
    }

    with Session(engine) as session:
        brand = session.exec(select(Brand).where(Brand.name == "Allen & Heath")).first()
        if not brand:
            print("Brand not found")
            return

        for prod_name, url in mapping.items():
            product = session.exec(select(Product).where(Product.name == prod_name)).first()
            if not product:
                print(f"Product {prod_name} not found in DB")
                continue
            
            # Check if document already exists for this product
            existing_doc = session.exec(select(Document).where(Document.product_id == product.id)).first()
            if existing_doc:
                print(f"Product {prod_name} already has a document")
                continue
            
            # Find the document by URL (it might be associated with the Group product)
            doc = session.exec(select(Document).where(Document.url == url)).first()
            if doc:
                print(f"Associating {prod_name} with existing document for {url}")
                # Create a new document entry for this product but with same content
                new_doc = Document(
                    title=doc.title,
                    url=doc.url,
                    content_hash=doc.content_hash,
                    last_updated=doc.last_updated,
                    brand_id=brand.id,
                    product_id=product.id
                )
                session.add(new_doc)
            else:
                print(f"Document for {url} not found in DB. Need to ingest it.")

        session.commit()
        print("Done fixing associations.")

if __name__ == "__main__":
    fix_missing()
