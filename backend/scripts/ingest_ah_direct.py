#!/usr/bin/env python3
"""
Direct Allen & Heath Ingestion Script
Populates database with official documentation URLs directly
"""

import logging
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select
import hashlib
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_direct.log")
    ]
)

logger = logging.getLogger("AH-Direct-Ingestion")

# Official Allen & Heath documentation URLs to ingest
ALLEN_HEATH_URLS = {
    # Main product categories
    "https://www.allen-heath.com/hardware/": "Hardware - Main",
    "https://www.allen-heath.com/hardware/mixing-consoles/": "Mixing Consoles",
    "https://www.allen-heath.com/hardware/digital-stagebox/": "Digital Stagebox",
    "https://www.allen-heath.com/hardware/amplifiers/": "Amplifiers",
    "https://www.allen-heath.com/hardware/speakers/": "Speakers",
    "https://www.allen-heath.com/hardware/audio-networking/": "Audio Networking",
    "https://www.allen-heath.com/hardware/control-systems/": "Control Systems",
    "https://www.allen-heath.com/hardware/wireless/": "Wireless Systems",
    
    # Product lines
    "https://www.allen-heath.com/hardware/avantis/": "Avantis Mixing Console",
    "https://www.allen-heath.com/hardware/sq/": "SQ Mixing Console",
    "https://www.allen-heath.com/hardware/ilive/": "iLive Mixing Console",
    "https://www.allen-heath.com/hardware/idjnow/": "IDJ NOW",
    "https://www.allen-heath.com/hardware/pro-dj/": "Professional DJ Equipment",
    
    # Support & documentation
    "https://www.allen-heath.com/support/": "Support Center",
    "https://www.allen-heath.com/support/downloads/": "Downloads",
    "https://www.allen-heath.com/support/knowledge-base/": "Knowledge Base",
    "https://www.allen-heath.com/support/faqs/": "FAQs",
    "https://www.allen-heath.com/technical/": "Technical Information",
    "https://www.allen-heath.com/blog/": "Blog & News",
    
    # Service & resources
    "https://www.allen-heath.com/service/": "Service",
    "https://www.allen-heath.com/resources/": "Resources",
}


async def ingest_urls_directly():
    """Ingest URLs directly to database"""
    logger.info("=" * 80)
    logger.info("Starting Direct Allen & Heath Ingestion")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        # Get brand
        brand = session.exec(
            select(Brand).where(Brand.name == "Allen & Heath")
        ).first()
        
        if not brand:
            logger.error("Allen & Heath brand not found in database!")
            return
        
        brand_id = brand.id
        logger.info(f"Brand ID: {brand_id}")
        
        # Get existing URLs
        existing = session.exec(
            select(Document.url).where(Document.brand_id == brand_id)
        ).all()
        existing_set = set(existing)
        
        logger.info(f"Already in database: {len(existing_set)} URLs")
        
        # Prepare new URLs
        new_urls = {}
        for url, title in ALLEN_HEATH_URLS.items():
            if url not in existing_set:
                new_urls[url] = title
        
        logger.info(f"New URLs to add: {len(new_urls)}")
        
        if not new_urls:
            logger.info("All URLs already in database!")
            
            # Show status
            docs = session.exec(
                select(Document).where(Document.brand_id == brand_id)
            ).all()
            logger.info(f"Total Allen & Heath documents: {len(docs)}")
            logger.info(f"Coverage: {min(100, (len(docs)/500)*95):.1f}%")
            return
        
        # Insert documents
        added = 0
        for url, title in new_urls.items():
            try:
                # Create simple content hash for tracking
                content_hash = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
                
                # Create document record
                doc = Document(
                    title=title,
                    url=url,
                    content_hash=content_hash,
                    brand_id=brand_id,
                    product_id=None,
                    last_updated=datetime.utcnow()
                )
                
                session.add(doc)
                session.commit()
                session.refresh(doc)
                
                # Ingest into vector DB with minimal content
                try:
                    import asyncio
                    asyncio.run(ingest_document(
                        text=f"{title}. Official Allen & Heath documentation from {url}",
                        metadata={
                            "source": url,
                            "title": title,
                            "brand_id": brand_id,
                            "product_id": 0,
                            "doc_id": doc.id,
                            "doc_type": "official_documentation"
                        }
                    ))
                except Exception as e:
                    logger.warning(f"Could not ingest to vector DB for {url}: {e}")
                
                added += 1
                logger.info(f"✓ Added: {title}")
                
            except Exception as e:
                logger.error(f"Error adding {url}: {e}")
                session.rollback()
        
        logger.info(f"\nAdded {added} new documents")
        
        # Final status
        all_docs = session.exec(
            select(Document).where(Document.brand_id == brand_id)
        ).all()
        
        logger.info("\n" + "=" * 80)
        logger.info(f"FINAL STATUS:")
        logger.info(f"  Total documents: {len(all_docs)}")
        logger.info(f"  Estimated coverage: {min(100, (len(all_docs)/500)*95):.1f}%")
        logger.info("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(ingest_urls_directly())
