from app.core.database import engine
from app.models.sql_models import Brand, Document
from sqlmodel import Session, select

with Session(engine) as session:
    brands = session.exec(select(Brand)).all()
    print(f"{'ID':<5} | {'Brand Name':<30} | {'Docs':<5}")
    print("-" * 45)
    for b in brands:
        docs_count = len(session.exec(select(Document).where(Document.brand_id == b.id)).all())
        print(f"{b.id:<5} | {b.name:<30} | {docs_count:<5}")
