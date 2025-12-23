import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from sqlmodel import select
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add the current directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_session, engine
from app.models.sql_models import Brand, Product, ProductFamily, Document
from app.services.pa_brands_scraper import PABrandsScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_technologies_ingestion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DB-Ingestor")

async def ingest_db_tech():
    scraper = PABrandsScraper()
    
    # Load links
    links_file = "/workspaces/Support-Center-/backend/data/db_technologies_links.txt"
    if not os.path.exists(links_file):
        logger.error(f"Links file {links_file} not found!")
        return

    with open(links_file, "r") as f:
        product_links = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Starting ingestion for {len(product_links)} dBTechnologies products")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        with next(get_session()) as session:
            brand = session.exec(select(Brand).where(Brand.name == "dBTechnologies")).first()
            if not brand:
                logger.error("Brand 'dBTechnologies' not found in database!")
                return

            for i, url in enumerate(product_links):
                logger.info(f"[{i+1}/{len(product_links)}] Processing: {url}")
                
                try:
                    # Check if already ingested
                    existing_doc = session.exec(select(Document).where(Document.url == url)).first()
                    if existing_doc:
                        logger.info(f"Skipping already ingested: {url}")
                        continue

                    # Extract name from URL
                    name = url.split('/')[-1].replace('-', ' ').title()
                    if not name or name == 'Products':
                        name = url.split('/')[-2].replace('-', ' ').title()

                    # Find or create product
                    product = session.exec(select(Product).where(Product.name == name)).first()
                    if not product:
                        family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == brand.id)).first()
                        if not family:
                            family = ProductFamily(name="dBTechnologies Products", brand_id=brand.id)
                            session.add(family)
                            session.commit()
                            session.refresh(family)
                        
                        product = Product(name=name, family_id=family.id)
                        session.add(product)
                        session.commit()
                        session.refresh(product)

                    # Scrape product page
                    try:
                        await scraper.scrape_generic_product_page(page, url, brand.id, product.id)
                        logger.info(f"Successfully ingested: {name}")
                    except Exception as e:
                        logger.error(f"Error scraping {url}: {e}")
                    
                    await asyncio.sleep(2) # Be nice

                except Exception as e:
                    logger.error(f"Unexpected error for {url}: {e}")
                    session.rollback()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(ingest_db_tech())
