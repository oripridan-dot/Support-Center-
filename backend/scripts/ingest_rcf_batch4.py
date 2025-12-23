import asyncio
import logging
from playwright.async_api import async_playwright
from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import get_session
from app.models.sql_models import Brand, Product, ProductFamily
from sqlmodel import select
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RCF-Batch-4")

async def ingest_batch(urls, brand_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        scraper = PABrandsScraper()
        
        for url in urls:
            page = await context.new_page()
            try:
                logger.info(f"Processing: {url}")
                name = url.split("/")[-1].replace("-", " ").title()
                
                with next(get_session()) as db:
                    stmt = select(Product).where(Product.name == name)
                    existing = db.exec(stmt).first()
                    if existing:
                        logger.info(f"Product {name} already exists, skipping.")
                        continue
                    
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
        brand_id = brand.id

    with open("rcf_links.txt", "r") as f:
        all_links = [line.strip() for line in f if line.strip()]

    # Batch 4: 750 to 1000
    target_links = all_links[750:1000]
    batch_size = 10
    
    for i in range(0, len(target_links), batch_size):
        batch = target_links[i:i+batch_size]
        logger.info(f"Starting batch {i//batch_size + 1} ({len(batch)} URLs)")
        try:
            await ingest_batch(batch, brand_id)
        except Exception as e:
            logger.error(f"Batch failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            try:
                await ingest_batch(batch, brand_id)
            except Exception as e2:
                logger.error(f"Batch failed again: {e2}. Skipping batch.")
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
