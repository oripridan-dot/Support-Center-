import asyncio
import os
import sys
import logging
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Add the current directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engines.wayback_scraper import WaybackScraper
from app.engines.ingestion_engine import IngestionEngine
from app.core.database import get_session, create_db_and_tables
from app.models.sql_models import Brand
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AH-Wayback-Ingestor")

async def ingest_ah_wayback():
    # Ensure DB tables exist
    create_db_and_tables()

    # Initialize Scraper and Engine
    scraper = WaybackScraper()
    engine = IngestionEngine(scraper)
    
    # Get Brand ID for Allen & Heath
    session = next(get_session())
    brand = session.exec(select(Brand).where(Brand.name == "Allen & Heath")).first()
    if not brand:
        logger.error("Brand 'Allen & Heath' not found in DB. Creating it.")
        brand = Brand(name="Allen & Heath", website_url="https://www.allen-heath.com")
        session.add(brand)
        session.commit()
        session.refresh(brand)
    
    brand_id = brand.id
    logger.info(f"Using Brand ID: {brand_id}")

    # Load links
    links_file = os.path.join(os.path.dirname(__file__), "../data/ah_wayback_links.txt")
    if not os.path.exists(links_file):
        logger.error(f"Links file {links_file} not found!")
        return

    with open(links_file, "r") as f:
        product_links = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Starting ingestion for {len(product_links)} Allen & Heath products via Wayback Machine")

    # Run ingestion
    # We process in chunks to avoid overwhelming anything (though Wayback is robust)
    chunk_size = 10
    for i in range(0, len(product_links), chunk_size):
        chunk = product_links[i:i+chunk_size]
        logger.info(f"Processing chunk {i//chunk_size + 1}...")
        await engine.run_ingestion(chunk, brand_id)
        
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(ingest_ah_wayback())
