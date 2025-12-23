import asyncio
import logging
import sys
import os

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import create_db_and_tables, Session, engine
from app.models.sql_models import Brand
from sqlmodel import select

async def main():
    logging.basicConfig(level=logging.INFO)
    create_db_and_tables()
    
    scraper = PABrandsScraper()
    
    # Modify scraper to do Mackie and RCF
    scraper.brands_to_scrape = [
        {"name": "Mackie", "url": "https://mackie.com/en/products"},
        {"name": "Rcf", "url": "https://www.rcf.it/en/products"}
    ]
    
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
