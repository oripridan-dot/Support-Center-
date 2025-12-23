import asyncio
import logging
import json
import datetime
import hashlib
from playwright.async_api import async_playwright
from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import get_session
from app.models.sql_models import Brand, Product, ProductFamily, Document
from app.services.rag_service import ingest_document
from sqlmodel import select
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion_robust.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MassIngestor")

class MassIngestor:
    def __init__(self, brand_name, links_file, concurrency=5):
        self.brand_name = brand_name
        self.links_file = links_file
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.failed_urls = []
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
        # Initialize DB connection for brand ID
        with next(get_session()) as db:
            stmt = select(Brand).where(Brand.name == brand_name)
            brand = db.exec(stmt).first()
            if not brand:
                # Try case insensitive
                stmt = select(Brand).where(Brand.name.ilike(brand_name))
                brand = db.exec(stmt).first()
                
            if not brand:
                logger.info(f"Brand {brand_name} not found, creating...")
                brand = Brand(name=brand_name, website_url="")
                db.add(brand)
                db.commit()
                db.refresh(brand)
            self.brand_id = brand.id
            logger.info(f"Initialized ingestor for {brand_name} (ID: {self.brand_id})")

    async def process_url(self, context, url):
        async with self.semaphore:
            page = await context.new_page()
            try:
                logger.info(f"Processing: {url}")
                
                # 1. Check if document exists and is fresh (simple URL check for now, ideally content hash)
                # For massive ingestion, we might want to skip if we scraped it recently (e.g. last 7 days)
                with next(get_session()) as db:
                    stmt = select(Document).where(Document.url == url).order_by(Document.last_updated.desc())
                    existing_doc = db.exec(stmt).first()
                    
                    if existing_doc:
                        # Check age
                        age = datetime.datetime.now() - existing_doc.last_updated
                        if age.days < 7:
                            logger.info(f"Skipping {url} - Scraped {age.days} days ago")
                            self.skipped_count += 1
                            return

                # 2. Prepare Product Entry
                name = url.split("/")[-1].replace("-", " ").replace(".html", "").title()
                if not name:
                    name = "Unknown Product"

                product_id = None
                with next(get_session()) as db:
                    # Check if product already exists
                    stmt = select(Product).where(Product.name == name)
                    existing_product = db.exec(stmt).first()
                    
                    if existing_product:
                        product_id = existing_product.id
                    else:
                        # Get or create family
                        stmt = select(ProductFamily).where(ProductFamily.brand_id == self.brand_id, ProductFamily.name == f"{self.brand_name} Products")
                        family = db.exec(stmt).first()
                        if not family:
                            family = ProductFamily(name=f"{self.brand_name} Products", brand_id=self.brand_id)
                            db.add(family)
                            db.commit()
                            db.refresh(family)
                        
                        product = Product(name=name, family_id=family.id)
                        db.add(product)
                        db.commit()
                        db.refresh(product)
                        product_id = product.id

                # 3. Scrape Data
                scraper = PABrandsScraper()
                # We are calling the existing method, but we need to handle the fact it does ingestion internally
                # Ideally we refactor PABrandsScraper, but for now we wrap it safely
                await scraper.scrape_generic_product_page(page, url, self.brand_id, product_id)
                
                self.processed_count += 1
                logger.info(f"Successfully processed {url}")

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                self.failed_urls.append(url)
                self.error_count += 1
            finally:
                await page.close()

    async def run(self):
        if not os.path.exists(self.links_file):
            logger.error(f"Links file {self.links_file} not found.")
            return

        with open(self.links_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]

        logger.info(f"Starting massive ingestion for {len(urls)} URLs with concurrency {self.concurrency}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            tasks = []
            for url in urls:
                tasks.append(self.process_url(context, url))
            
            await asyncio.gather(*tasks)
            
            await browser.close()

        logger.info("Ingestion Complete.")
        logger.info(f"Processed: {self.processed_count}")
        logger.info(f"Skipped: {self.skipped_count}")
        logger.info(f"Errors: {self.error_count}")
        
        if self.failed_urls:
            failed_file = f"{self.brand_name.lower()}_failed_urls.txt"
            with open(failed_file, "w") as f:
                for url in self.failed_urls:
                    f.write(f"{url}\n")
            logger.info(f"Failed URLs saved to {failed_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ingest_brand_robust.py <BrandName> <LinksFile>")
        sys.exit(1)
    
    brand = sys.argv[1]
    links = sys.argv[2]
    
    ingestor = MassIngestor(brand, links)
    asyncio.run(ingestor.run())
