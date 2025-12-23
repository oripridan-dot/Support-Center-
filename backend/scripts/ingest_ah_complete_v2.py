#!/usr/bin/env python3
"""
Allen & Heath Complete Ingestion - v2
Uses dedicated brand scraper with multi-browser support
Target: 500+ documents (95%+ coverage)
"""

import asyncio
import logging
import hashlib
from typing import Optional, Set
from datetime import datetime
from app.engines.ah_scraper import AllenHeathScraper
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_complete_v2.log")
    ]
)

logger = logging.getLogger("AH-Ingestion-v2")


class AllenHeathIngestionManager:
    """Manages complete Allen & Heath ingestion workflow"""
    
    def __init__(self):
        self.scraper = AllenHeathScraper(headless=True)
        self.ingested_urls: Set[str] = set()
        self.new_documents: int = 0
        self.failed_urls: Set[str] = set()
    
    async def run(self):
        """Execute complete ingestion workflow"""
        try:
            logger.info("="*70)
            logger.info("ALLEN & HEATH COMPLETE INGESTION - v2")
            logger.info("="*70)
            
            # Step 1: Initialize
            await self._initialize()
            
            # Step 2: Get or find Allen & Heath brand
            brand = self._get_ah_brand()
            if not brand:
                logger.error("Allen & Heath brand not found in database!")
                return
            
            # Step 3: Load already ingested URLs
            self._load_ingested_urls(brand.id)
            logger.info(f"Already ingested: {len(self.ingested_urls)} URLs")
            
            # Step 4: Discover URLs
            logger.info("\n" + "="*70)
            logger.info("PHASE 1: URL DISCOVERY")
            logger.info("="*70)
            discovered_urls = await self.scraper.discover_urls()
            
            # Filter to unprocessed URLs
            new_urls = [u for u in discovered_urls if u not in self.ingested_urls]
            logger.info(f"\nDiscovered {len(discovered_urls)} total URLs")
            logger.info(f"New URLs to ingest: {len(new_urls)}")
            
            if not new_urls:
                logger.info("No new URLs to ingest. Exiting.")
                return
            
            # Step 5: Ingest discovered URLs
            logger.info("\n" + "="*70)
            logger.info("PHASE 2: URL INGESTION")
            logger.info("="*70)
            await self._ingest_urls(brand, new_urls)
            
            # Step 6: Summary
            await self._print_summary(brand)
            
        except Exception as e:
            logger.error(f"Fatal error during ingestion: {e}", exc_info=True)
        finally:
            await self.scraper.stop()
    
    async def _initialize(self):
        """Initialize scraper"""
        logger.info("Initializing scraper...")
        await self.scraper.start()
        logger.info("✓ Scraper initialized")
    
    def _get_ah_brand(self) -> Optional[Brand]:
        """Get Allen & Heath brand from database"""
        with Session(engine) as session:
            result = session.exec(
                select(Brand).where(Brand.name == "Allen & Heath")
            ).first()
            return result
    
    def _load_ingested_urls(self, brand_id: int):
        """Load all already-ingested URLs for this brand"""
        with Session(engine) as session:
            docs = session.exec(
                select(Document).where(Document.brand_id == brand_id)
            ).all()
            self.ingested_urls = {doc.url for doc in docs if doc.url}
    
    async def _ingest_urls(self, brand: Brand, urls: list):
        """Ingest a batch of URLs"""
        batch_size = 10
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(urls) - 1) // batch_size + 1
            
            logger.info(f"\nBatch {batch_num}/{total_batches} ({len(batch)} URLs)")
            logger.info("-" * 70)
            
            # Scrape batch with dedup
            for j, url in enumerate(batch):
                try:
                    logger.info(f"  [{j+1}/{len(batch)}] {url.split('/')[-1][:50]}")
                    
                    # Scrape with deduplication
                    html = await self.scraper.scrape_with_dedup(url)
                    if not html:
                        logger.debug(f"      → Skipped (duplicate or failed)")
                        continue
                    
                    # Extract text content
                    text_content = self._extract_text(html)
                    if not text_content or len(text_content.strip()) < 100:
                        logger.debug(f"      → Skipped (insufficient content)")
                        continue
                    
                    # Extract title
                    title = self._extract_title(html, url)
                    
                    # Ingest into SQL database
                    with Session(engine) as session:
                        doc = Document(
                            brand_id=brand.id,
                            title=title,
                            content=text_content,
                            url=url
                        )
                        session.add(doc)
                        session.commit()
                        session.refresh(doc)
                        doc_id = doc.id
                    
                    # Ingest into vector DB (ChromaDB)
                    try:
                        await ingest_document(
                            text=text_content,
                            metadata={
                                "source": url,
                                "title": title,
                                "brand_id": brand.id,
                                "brand": brand.name,
                                "doc_id": doc_id
                            }
                        )
                    except Exception as ve:
                        logger.warning(f"      ⚠ Vector DB ingestion warning: {str(ve)[:60]}")
                    
                    self.new_documents += 1
                    self.ingested_urls.add(url)
                    logger.info(f"      ✓ Ingested (doc_id={doc_id})")
                    
                except Exception as e:
                    logger.error(f"      ✗ Error: {str(e)[:80]}")
                    self.failed_urls.add(url)
            
            # Delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(5)
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style tags
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        except:
            return ""
    
    def _extract_title(self, html: str, url: str) -> str:
        """Extract title from HTML or URL"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.text.strip()
        except:
            pass
        
        # Fallback: use URL
        return url.split('/')[-1].replace('-', ' ').title()[:100]
    
    async def _print_summary(self, brand: Brand):
        """Print ingestion summary"""
        with Session(engine) as session:
            total_docs = session.exec(
                select(Document).where(Document.brand_id == brand.id)
            ).all()
            
            logger.info("\n" + "="*70)
            logger.info("INGESTION SUMMARY")
            logger.info("="*70)
            logger.info(f"Brand: {brand.name}")
            logger.info(f"New documents ingested: {self.new_documents}")
            logger.info(f"Total documents now: {len(total_docs)}")
            logger.info(f"Coverage: {min(100, (len(total_docs)/500)*100):.1f}%")
            logger.info(f"Failed URLs: {len(self.failed_urls)}")
            logger.info("="*70)
            
            if self.failed_urls:
                logger.warning("Failed URLs:")
                for url in sorted(self.failed_urls)[:10]:
                    logger.warning(f"  - {url}")


async def main():
    """Main entry point"""
    manager = AllenHeathIngestionManager()
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())
