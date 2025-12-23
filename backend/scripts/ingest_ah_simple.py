#!/usr/bin/env python3
"""
Simple Allen & Heath Ingestion Script
Uses existing discovered links and focuses on robustness
"""

import asyncio
import logging
from app.engines.ingestion_engine import IngestionEngine
from app.engines.base_scraper import BaseScraper
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_simple.log")
    ]
)

logger = logging.getLogger("AH-Simple-Ingestion")


class SimpleAHScraper(BaseScraper):
    """Simple scraper using predefined URLs"""
    
    def __init__(self):
        super().__init__()
        self.base_urls = [
            "https://www.allen-heath.com/hardware/",
            "https://www.allen-heath.com/support/",
            "https://www.allen-heath.com/downloads/",
        ]


async def main():
    logger.info("=" * 80)
    logger.info("Starting Simple Allen & Heath Ingestion")
    logger.info("=" * 80)
    
    # Get or create brand
    with Session(engine) as session:
        brand = session.exec(
            select(Brand).where(Brand.name == "Allen & Heath")
        ).first()
        
        if not brand:
            logger.error("Allen & Heath brand not found in database!")
            return
        
        brand_id = brand.id
        logger.info(f"Using brand ID: {brand_id}")
        
        # Get existing ingested URLs
        existing_docs = session.exec(
            select(Document).where(Document.brand_id == brand_id)
        ).all()
        existing_urls = {doc.url for doc in existing_docs}
        
        logger.info(f"Already ingested: {len(existing_urls)} URLs")
        current_count = len(existing_docs)
    
    # Use existing scraper infrastructure
    scraper = SimpleAHScraper()
    engine_obj = IngestionEngine(scraper)
    
    # Define comprehensive Allen & Heath sections to ingest
    urls_to_ingest = [
        # Main hardware pages
        "https://www.allen-heath.com/hardware/",
        "https://www.allen-heath.com/hardware/mixing-consoles/",
        "https://www.allen-heath.com/hardware/digital-stagebox/",
        "https://www.allen-heath.com/hardware/amplifiers/",
        "https://www.allen-heath.com/hardware/speakers/",
        
        # Support pages
        "https://www.allen-heath.com/support/",
        "https://www.allen-heath.com/support/downloads/",
        "https://www.allen-heath.com/support/knowledge-base/",
        
        # Product categories
        "https://www.allen-heath.com/hardware/ipv4/",
        "https://www.allen-heath.com/hardware/ilive/",
        "https://www.allen-heath.com/hardware/sq/",
        "https://www.allen-heath.com/hardware/avantis/",
    ]
    
    # Filter out already ingested
    new_urls = [url for url in urls_to_ingest if url not in existing_urls]
    logger.info(f"New URLs to ingest: {len(new_urls)}")
    
    if not new_urls:
        logger.info("All known URLs already ingested!")
        
        # Show current status
        with Session(engine) as session:
            docs = session.exec(
                select(Document).where(Document.brand_id == brand_id)
            ).all()
            logger.info(f"Current total: {len(docs)} documents")
        return
    
    # Ingest new URLs
    logger.info(f"Starting ingestion of {len(new_urls)} new URLs...")
    try:
        results = await engine_obj.run_ingestion(new_urls, brand_id)
        successful = sum(1 for r in results if r)
        logger.info(f"Ingestion complete: {successful}/{len(new_urls)} successful")
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        return
    
    # Final count
    with Session(engine) as session:
        final_docs = session.exec(
            select(Document).where(Document.brand_id == brand_id)
        ).all()
        final_count = len(final_docs)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"FINAL RESULT: {final_count} documents for Allen & Heath")
        logger.info(f"Added: {final_count - current_count} new documents")
        logger.info(f"Estimated coverage: {min(100, (final_count/500)*95):.1f}%")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
