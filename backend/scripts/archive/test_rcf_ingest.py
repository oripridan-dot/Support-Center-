import asyncio
import logging
import os
import sys
from playwright.async_api import async_playwright

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import get_session
from app.models.sql_models import Brand, Product, Document
from sqlmodel import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RCF-Test")

async def test_ingest():
    url = "https://www.rcf.it/en/products/product-detail/l-pad-6"
    brand_name = "RCF"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        scraper = PABrandsScraper()
        
        with next(get_session()) as db:
            brand = db.exec(select(Brand).where(Brand.name == brand_name)).first()
            product = db.exec(select(Product).where(Product.name == "L Pad 6")).first()
            
            if not product:
                print("Product L Pad 6 not found in DB")
                return
                
            print(f"Testing ingestion for {url} (Product ID: {product.id})")
            
            # Delete existing doc if any (should be none)
            existing_docs = db.exec(select(Document).where(Document.product_id == product.id)).all()
            for doc in existing_docs:
                db.delete(doc)
            db.commit()
            
            try:
                await scraper.scrape_generic_product_page(page, url, brand.id, product.id)
                print("Scrape completed")
                
                # Check if doc was created
                doc = db.exec(select(Document).where(Document.product_id == product.id)).first()
                if doc:
                    print(f"Success! Document created: {doc.title}")
                else:
                    print("Failure: No document created")
            except Exception as e:
                print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ingest())
