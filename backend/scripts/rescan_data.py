import asyncio
import os
import sys
import logging
import chromadb
from sqlmodel import Session, select, delete

# Add the current directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import engine
from app.models.sql_models import Document, Product, Brand, ProductFamily
from app.core.vector_db import client
from app.services.pa_brands_scraper import PABrandsScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Rescan")

async def clear_data():
    logger.info("Clearing existing data...")
    
    # 1. Clear ChromaDB
    try:
        client.delete_collection("support_docs")
        logger.info("ChromaDB collection deleted.")
    except Exception as e:
        logger.warning(f"Could not delete ChromaDB collection: {e}")
    
    client.get_or_create_collection("support_docs")
    logger.info("ChromaDB collection recreated.")

    # 2. Clear Document table in SQL
    with Session(engine) as session:
        session.exec(delete(Document))
        session.commit()
        logger.info("SQL Document table cleared.")

async def rescan():
    await clear_data()
    
    # 3. Re-run ingestion using the improved PABrandsScraper
    logger.info("Starting re-ingestion...")
    scraper = PABrandsScraper(force_rescan=True)
    await scraper.run()

    logger.info("Rescan complete!")

if __name__ == "__main__":
    asyncio.run(rescan())
