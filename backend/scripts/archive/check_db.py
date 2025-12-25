from sqlmodel import Session, create_engine, select
from app.models import Product

engine = create_engine("sqlite:///database.db")

with Session(engine) as session:
    statement = select(Product).where(Product.brand_id == "allen-heath").limit(10)
    results = session.exec(statement).all()
    for product in results:
        print(f"Product: {product.name}, Image: {product.image_url}")
