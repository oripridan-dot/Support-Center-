import asyncio
import logging
import os
import sys
from playwright.async_api import async_playwright

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import get_session
from app.models.sql_models import Brand, Product, ProductFamily, Document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rcf_ingestion_full.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RCF-Ingestor")

async def ingest_batch(urls, brand_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        scraper = PABrandsScraper()
        
        for url in urls:
            page = await context.new_page()
            try:
                with next(get_session()) as db:
                    # Check if URL already ingested
                    existing_doc = db.exec(select(Document).where(Document.url == url)).first()
                    if existing_doc:
                        logger.info(f"URL already ingested, skipping: {url}")
                        continue

                    logger.info(f"Processing: {url}")
                    # Extract product name from URL
                    name = url.split("/")[-1].replace("-", " ").title()
                    if not name or name == 'Products':
                        name = url.split('/')[-2].replace('-', ' ').title()
                    
                    # Check if product already exists by name
                    stmt = select(Product).where(Product.name == name)
                    product = db.exec(stmt).first()
                    
                    if not product:
                        # Get or create family (Generic for now)
                        stmt = select(ProductFamily).where(ProductFamily.brand_id == brand_id, ProductFamily.name == "RCF Products")
                        family = db.exec(stmt).first()
                        if not family:
                            family = ProductFamily(name="RCF Products", brand_id=brand_id)
                            db.add(family)
                            db.commit()
                            db.refresh(family)
                        
                        product = Product(name=name, family_id=family.id)
                        db.add(product)
                        db.commit()
                        db.refresh(product)
                    
                    await scraper.scrape_generic_product_page(page, url, brand_id, product.id)
                    logger.info(f"Successfully ingested {name}")
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
            finally:
                await page.close()
        
        await browser.close()

async def main():
    brand_name = "RCF"
    with next(get_session()) as db:
        stmt = select(Brand).where(Brand.name == brand_name)
        brand = db.exec(stmt).first()
        if not brand:
            brand = Brand(name=brand_name, website_url="https://www.rcf.it")
            db.add(brand)
            db.commit()
            db.refresh(brand)
        brand_id = brand.id

    with open("/workspaces/Support-Center-/backend/data/rcf_links_en.txt", "r") as f:
        all_links = [line.strip() for line in f if line.strip()]

    # Process all links
    target_links = all_links
    batch_size = 5
    
    for i in range(0, len(target_links), batch_size):
        batch = target_links[i:i+batch_size]
        logger.info(f"Starting batch {i//batch_size + 1} / {len(target_links)//batch_size + 1}")
        try:
            await ingest_batch(batch, brand_id)
        except Exception as e:
            logger.error(f"Batch failed: {e}. Retrying in 10 seconds...")
            await asyncio.sleep(10)
            try:
                await ingest_batch(batch, brand_id)
            except Exception as e2:
                logger.error(f"Batch failed again: {e2}. Skipping batch.")
        await asyncio.sleep(1) # Small gap between batches

if __name__ == "__main__":
    asyncio.run(main())
