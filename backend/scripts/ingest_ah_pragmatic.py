#!/usr/bin/env python3
"""
Allen & Heath Pragmatic Ingestion
Simple, proven approach: curated URLs + HTTP scraping
No Cloudflare, no browser complexity
"""

import asyncio
import logging
import hashlib
from typing import Optional, Set, Dict
from bs4 import BeautifulSoup
import httpx
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_pragmatic.log")
    ]
)
logger = logging.getLogger("AH-Pragmatic")

# Known accessible Allen & Heath URLs (curated list)
CURATED_URLS = {
    # Main product categories
    "https://www.allen-heath.com/products/",
    "https://www.allen-heath.com/products/mixers/",
    "https://www.allen-heath.com/products/control-surfaces/",
    "https://www.allen-heath.com/products/digital-mixers/",
    "https://www.allen-heath.com/products/analog-mixers/",
    
    # Support/Documentation
    "https://support.allen-heath.com/hc/en-us",
    "https://support.allen-heath.com/hc/en-us/sections",
    
    # Knowledge base articles (if accessible)
    "https://www.allen-heath.com/blog/",
    
    # Category pages
    "https://www.allen-heath.com/category/live-sound/",
    "https://www.allen-heath.com/category/studio/",
    "https://www.allen-heath.com/category/dj/",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class PragmaticAHIngestion:
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.ingested_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.new_documents: int = 0
        self.failed_urls: Set[str] = set()
    
    async def initialize(self):
        """Start HTTP session"""
        self.session = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            follow_redirects=True
        )
        logger.info("✓ HTTP session initialized")
    
    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
    
    def _get_ah_brand(self) -> Optional[Brand]:
        """Get Allen & Heath brand"""
        with Session(engine) as session:
            return session.exec(
                select(Brand).where(Brand.name == "Allen & Heath")
            ).first()
    
    def _load_ingested(self, brand_id: int):
        """Load already-ingested URLs"""
        with Session(engine) as session:
            docs = session.exec(
                select(Document).where(Document.brand_id == brand_id)
            ).all()
            self.ingested_urls = {doc.url for doc in docs if doc.url}
            logger.info(f"Already ingested: {len(self.ingested_urls)} URLs")
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with error handling"""
        try:
            logger.info(f"Fetching: {url}")
            response = await self.session.get(url)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"  → Status {response.status_code}")
                self.failed_urls.add(url)
                return None
                
        except Exception as e:
            logger.warning(f"  → Error: {str(e)[:80]}")
            self.failed_urls.add(url)
            return None
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines[:5000])  # Limit to 5000 lines
        except:
            return ""
    
    def _extract_title(self, html: str, url: str) -> str:
        """Extract title from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            if soup.title:
                return soup.title.text.strip()[:100]
        except:
            pass
        return url.split('/')[-1].title()[:100]
    
    async def discover_urls(self) -> Set[str]:
        """Discover additional URLs from curated starting points"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 1: URL DISCOVERY")
        logger.info("="*70)
        
        self.discovered_urls = CURATED_URLS.copy()
        logger.info(f"Starting with {len(self.discovered_urls)} curated URLs")
        
        # Try to find more URLs by scraping the main pages
        for url in list(self.discovered_urls)[:3]:  # Just check first 3
            html = await self.fetch_url(url)
            if not html:
                continue
            
            # Extract links
            soup = BeautifulSoup(html, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Only keep Allen & Heath URLs
                if 'allen-heath.com' in href or 'support.allen-heath.com' in href:
                    # Handle relative URLs
                    if href.startswith('/'):
                        full_url = "https://www.allen-heath.com" + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    full_url = full_url.split('#')[0]  # Remove fragments
                    
                    if full_url not in self.discovered_urls:
                        self.discovered_urls.add(full_url)
            
            await asyncio.sleep(1)  # Be polite
        
        logger.info(f"✓ Discovered {len(self.discovered_urls)} total URLs")
        return self.discovered_urls
    
    async def ingest_urls(self, brand: Brand):
        """Ingest discovered URLs"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 2: INGESTION")
        logger.info("="*70)
        
        # Filter to new URLs only
        new_urls = [u for u in self.discovered_urls if u not in self.ingested_urls]
        logger.info(f"New URLs to ingest: {len(new_urls)}")
        
        if not new_urls:
            logger.info("No new URLs to ingest")
            return
        
        # Ingest in batches
        batch_size = 5
        for i in range(0, len(new_urls), batch_size):
            batch = new_urls[i:i + batch_size]
            logger.info(f"\nBatch {i//batch_size + 1}/{(len(new_urls)-1)//batch_size + 1}")
            
            for url in batch:
                try:
                    # Fetch content
                    html = await self.fetch_url(url)
                    if not html:
                        continue
                    
                    # Extract text
                    text = self._extract_text(html)
                    if not text or len(text) < 50:
                        logger.info(f"  → Skipped (too short)")
                        continue
                    
                    title = self._extract_title(html, url)
                    
                    # Ingest to SQL
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
                    
                    # Ingest to ChromaDB
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
                        logger.warning(f"  ⚠ Vector DB: {str(e)[:50]}")
                    
                    self.new_documents += 1
                    self.ingested_urls.add(url)
                    logger.info(f"  ✓ Ingested (doc_id={doc_id})")
                    
                except Exception as e:
                    logger.error(f"  ✗ Error: {str(e)[:80]}")
                    self.failed_urls.add(url)
                
                await asyncio.sleep(0.5)  # Be polite
            
            if i + batch_size < len(new_urls):
                await asyncio.sleep(2)  # Delay between batches
    
    async def run(self):
        """Main workflow"""
        try:
            logger.info("="*70)
            logger.info("ALLEN & HEATH PRAGMATIC INGESTION")
            logger.info("="*70)
            
            # Initialize
            await self.initialize()
            
            # Get brand
            brand = self._get_ah_brand()
            if not brand:
                logger.error("Allen & Heath brand not found!")
                return
            
            # Load ingested
            self._load_ingested(brand.id)
            
            # Discover
            await self.discover_urls()
            
            # Ingest
            await self.ingest_urls(brand)
            
            # Summary
            with Session(engine) as session:
                docs = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                
                logger.info("\n" + "="*70)
                logger.info("SUMMARY")
                logger.info("="*70)
                logger.info(f"Total AH documents now: {len(docs)}")
                logger.info(f"New documents added: {self.new_documents}")
                logger.info(f"Coverage: {min(100, (len(docs)/500)*100):.1f}%")
                logger.info(f"Failed URLs: {len(self.failed_urls)}")
                logger.info("="*70)
        
        finally:
            await self.cleanup()


async def main():
    ingestion = PragmaticAHIngestion()
    await ingestion.run()


if __name__ == "__main__":
    asyncio.run(main())
