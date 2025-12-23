import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag_service import ask_question
from app.core.database import get_session
from app.models.sql_models import Brand, Product
from sqlmodel import select

async def test_scenario():
    question = "What are the specifications of the RCF 2 2 C?"
    print(f"--- Asking: {question} ---")
    
    # Find RCF brand id
    with next(get_session()) as db:
        brand = db.exec(select(Brand).where(Brand.name == "RCF")).first()
        brand_id = brand.id if brand else None
        
        # Find product id for 2 2 C
        product = db.exec(select(Product).where(Product.name == "2 2 C")).first()
        product_id = product.id if product else None

    response = await ask_question(
        question=question,
        brand_id=brand_id,
        product_id=product_id,
        is_first_message=True
    )
    
    print("\n--- Response ---")
    print(response["answer"])
    
    print("\n--- Sources ---")
    for source in response["sources"]:
        print(f"- {source.get('url', 'No URL')}")
        
    print("\n--- Images ---")
    for img in response["images"]:
        print(f"- {img['url']}")

    print("\n--- PDFs ---")
    for pdf in response["pdfs"]:
        print(f"- {pdf['title']}: {pdf['url']}")

    print("\n--- Brand Logos ---")
    if "brand_logos" in response:
        for logo in response["brand_logos"]:
            print(f"- {logo['name']}: {logo['url']}")

if __name__ == "__main__":
    asyncio.run(test_scenario())
