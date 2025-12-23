from app.core.database import get_session
from app.models.sql_models import Brand, Product, ProductFamily, Document
from sqlmodel import select

def check_rcf_status():
    with next(get_session()) as db:
        brand = db.exec(select(Brand).where(Brand.name == "RCF")).first()
        if not brand:
            print("RCF brand not found.")
            return

        products = db.exec(select(Product).join(ProductFamily).where(ProductFamily.brand_id == brand.id)).all()
        documents = db.exec(select(Document).where(Document.brand_id == brand.id)).all()

        print(f"RCF Brand ID: {brand.id}")
        print(f"Total RCF Products in DB: {len(products)}")
        print(f"Total RCF Documents in DB: {len(documents)}")
        
        if documents:
            print("Sample Document URLs:")
            for doc in documents[:5]:
                print(f"- {doc.url}")

if __name__ == "__main__":
    check_rcf_status()
