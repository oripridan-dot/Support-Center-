from sqlmodel import Session, select, create_engine
from app.models.sql_models import Brand, Document

# Adjust the database URL if necessary. Assuming sqlite:///support_center.db based on file list
engine = create_engine("sqlite:///support_center.db")

with Session(engine) as session:
    brands = session.exec(select(Brand)).all()
    print("Brands:")
    for b in brands:
        print(f"ID: {b.id}, Name: {b.name}")

    print("\nRecent Documents:")
    docs = session.exec(select(Document).order_by(Document.id.desc()).limit(10)).all()
    for d in docs:
        print(f"ID: {d.id}, Title: {d.title}, BrandID: {d.brand_id}, URL: {d.url}")
