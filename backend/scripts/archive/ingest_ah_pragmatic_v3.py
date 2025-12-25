#!/usr/bin/env python3
"""
Allen & Heath Pragmatic Ingestion - v3
Uses pre-discovered URLs + intelligent HTTP/Browser fallback
Focuses on reliability over comprehensive discovery
"""

import asyncio
import logging
from typing import Set
from app.engines.ah_scraper import AllenHeathScraper
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_pragmatic_v3.log")
    ]
)

logger = logging.getLogger("AH-Pragmatic-v3")


class PragmaticAHIngestion:
    """Pragmatic approach: Known URLs + smart fallback"""
    
    # Pre-discovered known good AH URLs (from robots.txt + manual knowledge)
    KNOWN_URLS = {
        "https://www.allen-heath.com",
        "https://www.allen-heath.com/products/",
        "https://www.allen-heath.com/support/",
        "https://www.allen-heath.com/downloads/",
        "https://www.allen-heath.com/blog/",
        "https://www.allen-heath.com/category/live-sound/",
        "https://www.allen-heath.com/category/studio/",
        "https://www.allen-heath.com/category/dj/",
        "https://www.allen-heath.com/category/education/",
    }
    
    def __init__(self):
        self.scraper = AllenHeathScraper(headless=True)
        self.new_documents = 0
        self.skipped = 0
        self.failed = 0
    
    async def run(self):
        """Run pragmatic ingestion"""
        try:
            logger.info("="*70)
            logger.info("ALLEN & HEATH PRAGMATIC INGESTION - v3")
            logger.info("="*70)
            
            # Initialize
            await self.scraper.start()
            logger.info("✓ Scraper initialized\n")
            
            # Get brand
            with Session(engine) as session:
                brand = session.exec(
                    select(Brand).where(Brand.name == "Allen & Heath")
                ).first()
                if not brand:
                    logger.error("Brand not found!")
                    return
            
            # Load already-ingested
            with Session(engine) as session:
                docs = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                ingested = {doc.url for doc in docs if doc.url}
            
            logger.info(f"Already ingested: {len(ingested)} URLs\n")
            
            # Filter to new URLs
            new_urls = [u for u in self.KNOWN_URLS if u not in ingested]
            logger.info(f"Known URLs to process: {len(new_urls)}\n")
            logger.info("="*70)
            logger.info("PHASE 1: INGESTING KNOWN URLS")
            logger.info("="*70)
            
            # Ingest known URLs
            for url in new_urls:
                await self._ingest_single_url(brand, url)
            
            # Phase 2: Follow internal links
            logger.info("\n" + "="*70)
            logger.info("PHASE 2: DISCOVERING INTERNAL LINKS FROM KNOWN URLS")
            logger.info("="*70)
            
            discovered = set()
            for url in new_urls:
                new_urls_from_page = await self._extract_links(url)
                discovered.update(new_urls_from_page)
            
            logger.info(f"\n✓ Discovered {len(discovered)} new internal links")
            
            # Filter and ingest discovered
            discovered_new = [u for u in discovered if u not in ingested and u not in new_urls]
            logger.info(f"New discovered URLs to ingest: {len(discovered_new)}\n")
            
            for i, url in enumerate(discovered_new[:200], 1):  # Limit to 200
                logger.info(f"[{i}] {url}")
                await self._ingest_single_url(brand, url)
                
                # Polite delay
                if i % 10 == 0:
                    await asyncio.sleep(5)
            
            # Summary
            logger.info("\n" + "="*70)
            logger.info("INGESTION SUMMARY")
            logger.info("="*70)
            logger.info(f"New documents: {self.new_documents}")
            logger.info(f"Skipped: {self.skipped}")
            logger.info(f"Failed: {self.failed}")
            
            with Session(engine) as session:
                total = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                logger.info(f"Total documents now: {len(total)}")
                logger.info(f"Coverage: {min(100, (len(total)/500)*100):.1f}%")
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            await self.scraper.stop()
    
    async def _ingest_single_url(self, brand, url: str):
        """Ingest a single URL"""
        try:
            # Try HTTP first
            html = await self.scraper._get_content_http(url)
            
            # Fall back to browser
            if not html:
                html = await self.scraper.scrape_url(url)
            
            if not html:
                logger.warning(f"✗ Failed to scrape: {url}")
                self.failed += 1
                return
            
            # Extract content
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            text = '\n'.join(line.strip() for line in soup.get_text(separator='\n').split('\n') if line.strip())
            
            if not text or len(text) < 100:
                logger.debug(f"⊘ Skipped (insufficient content): {url}")
                self.skipped += 1
                return
            
            # Extract title
            title = url.split('/')[-1].replace('-', ' ').title()[:100]
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.text.strip()[:100]
            
            # Store in database
            with Session(engine) as session:
                doc = Document(
                    brand_id=brand.id,
                    title=title,
                    content=text,
                    url=url
                )
                session.add(doc)
                session.commit()
                session.refresh(doc)
                doc_id = doc.id
            
            # Index in vector DB
            try:
                await ingest_document(
                    text=text,
                    metadata={
                        "source": url,
                        "title": title,
                        "brand_id": brand.id,
                        "brand": "Allen & Heath",
                        "doc_id": doc_id
                    }
                )
            except Exception as e:
                logger.debug(f"Vector DB warning: {str(e)[:60]}")
            
            self.new_documents += 1
            logger.info(f"✓ Ingested: {title[:50]}")
            
        except Exception as e:
            logger.error(f"✗ Error ingesting {url}: {str(e)[:80]}")
            self.failed += 1
    
    async def _extract_links(self, url: str) -> Set[str]:
        """Extract internal links from a URL"""
        try:
            html = await self.scraper._get_content_http(url)
            if not html:
                html = await self.scraper.scrape_url(url)
            
            if not html:
                return set()
            
            soup = BeautifulSoup(html, 'html.parser')
            links = set()
            
            from urllib.parse import urljoin
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin("https://www.allen-heath.com", href)
                absolute_url = absolute_url.split('#')[0]  # Remove fragments
                
                if self.scraper.is_valid_url(absolute_url):
                    links.add(absolute_url)
            
            return links
            
        except Exception as e:
            logger.debug(f"Error extracting links from {url}: {e}")
            return set()


async def main():
    ingestion = PragmaticAHIngestion()
    await ingestion.run()


if __name__ == "__main__":
    asyncio.run(main())
