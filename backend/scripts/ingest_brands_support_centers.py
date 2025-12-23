#!/usr/bin/env python3
"""
Multi-Brand Support Center Ingestion
Ingests from official support centers (Zendesk-based)
Optimized for maximum coverage with proven Playwright approach
"""

import asyncio
import logging
from typing import Set, Optional
from datetime import datetime
import hashlib
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_brands_support.log")
    ]
)

logger = logging.getLogger("Brand-Support-Ingestion")

# Brand support center configurations
BRAND_CONFIGS = {
    "Allen & Heath": {
        "brand_id": 28,
        "base_url": "https://support.allen-heath.com/hc/en-us",
        "main_page": "https://support.allen-heath.com/hc/en-us",
        "category_limit": 10,
        "articles_per_category": 50,
    },
    "RCF": {
        "brand_id": 88,  # RCF brand ID
        "base_url": "https://rcf.zendesk.com/hc/en-us",
        "main_page": "https://rcf.zendesk.com/hc/en-us",
        "category_limit": 10,
        "articles_per_category": 50,
    },
}

class SupportCenterIngester:
    def __init__(self, brand_name: str, config: dict):
        self.brand_name = brand_name
        self.config = config
        self.browser: Optional[Browser] = None
        self.session = None
        self.ingested_urls: Set[str] = set()
        
    async def start(self):
        """Initialize browser and database session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        self.session = Session(engine)
        logger.info(f"✓ Started ingester for {self.brand_name}")
        
    async def stop(self):
        """Cleanup"""
        if self.browser:
            await self.browser.close()
        if self.session:
            self.session.close()
            
    async def fetch_page(self, url: str) -> str:
        """Fetch page with Playwright"""
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)  # Wait for dynamic content
            content = await page.content()
            return content
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return ""
        finally:
            await page.close()
            
    def _extract_text(self, html: str, max_lines: int = 5000) -> str:
        """Extract clean text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Remove script and style tags
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = soup.get_text('\n', strip=True)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            return '\n'.join(lines[:max_lines])
        except:
            return ""
            
    async def discover_articles(self) -> Set[str]:
        """Discover all articles from support center"""
        logger.info(f"📖 PHASE 1: Discovering {self.brand_name} articles...")
        articles = set()
        
        # Fetch main page
        html = await self.fetch_page(self.config["main_page"])
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract article links from main page
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/hc/' in href and '/articles/' in href:
                full_url = href if href.startswith('http') else f"{self.config['base_url']}{href}"
                articles.add(full_url)
                
        logger.info(f"  ✓ Found {len(articles)} articles on main page")
        
        # Find category pages and extract from each
        categories = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/categories/' in href or '/sections/' in href:
                full_url = href if href.startswith('http') else f"{self.config['base_url']}{href}"
                categories.add(full_url)
                
        logger.info(f"  ✓ Found {len(categories)} category pages")
        
        # Process each category
        for i, category_url in enumerate(list(categories)[:self.config["category_limit"]]):
            logger.info(f"  → Category {i+1}/{min(len(categories), self.config['category_limit'])}: {category_url}")
            html = await self.fetch_page(category_url)
            soup = BeautifulSoup(html, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/articles/' in href:
                    full_url = href if href.startswith('http') else f"{self.config['base_url']}{href}"
                    articles.add(full_url)
                    
        logger.info(f"  ✓ Total articles discovered: {len(articles)}")
        return articles
        
    async def ingest_articles(self, article_urls: Set[str]):
        """Ingest all articles into database"""
        brand = self.session.exec(select(Brand).where(Brand.name == self.brand_name)).first()
        if not brand:
            logger.error(f"Brand {self.brand_name} not found")
            return
            
        # Load already ingested URLs
        existing_docs = self.session.exec(
            select(Document).where(Document.brand_id == brand.id)
        ).all()
        self.ingested_urls = {doc.url for doc in existing_docs}
        
        new_urls = [url for url in article_urls if url not in self.ingested_urls]
        logger.info(f"📝 PHASE 2: Ingesting {len(new_urls)} new articles for {self.brand_name}...")
        
        # Batch process
        batch_size = 5
        for i in range(0, len(new_urls), batch_size):
            batch = new_urls[i:i + batch_size]
            for url in batch:
                try:
                    html = await self.fetch_page(url)
                    if not html:
                        continue
                        
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('h1')
                    title = title_tag.text.strip() if title_tag else "Untitled"
                    
                    # Extract content
                    content_div = soup.find('div', {'class': ['article-body', 'article-content']})
                    if not content_div:
                        content_div = soup.find('main')
                    
                    content_text = self._extract_text(str(content_div)) if content_div else ""
                    content_hash = hashlib.md5(content_text.encode()).hexdigest()
                    
                    # Create and save document
                    doc = Document(
                        brand_id=brand.id,
                        title=title,
                        url=url,
                        content=content_text,
                        content_hash=content_hash,
                    )
                    self.session.add(doc)
                    self.session.commit()
                    
                    logger.info(f"  ✓ Ingested: {title[:50]}")
                    
                except Exception as e:
                    logger.error(f"Error ingesting {url}: {e}")
                    self.session.rollback()
                    
            logger.info(f"  → Batch {i//batch_size + 1}: {min(batch_size, len(new_urls)-i)} articles")
            
    async def ingest_brand(self):
        """Complete ingestion pipeline for brand"""
        logger.info(f"\n{'='*70}")
        logger.info(f"{self.brand_name.upper()} INGESTION STARTING")
        logger.info(f"{'='*70}")
        
        try:
            await self.start()
            articles = await self.discover_articles()
            await self.ingest_articles(articles)
            logger.info(f"✅ {self.brand_name} ingestion complete!")
        finally:
            await self.stop()


async def main():
    logger.info("\n" + "="*70)
    logger.info("MULTI-BRAND SUPPORT CENTER INGESTION")
    logger.info("="*70)
    
    for brand_name, config in BRAND_CONFIGS.items():
        ingester = SupportCenterIngester(brand_name, config)
        await ingester.ingest_brand()
        
    # Final summary
    logger.info("\n" + "="*70)
    logger.info("INGESTION SUMMARY")
    logger.info("="*70)
    
    session = Session(engine)
    for brand_name, config in BRAND_CONFIGS.items():
        brand = session.exec(select(Brand).where(Brand.name == brand_name)).first()
        if brand:
            doc_count = len(session.exec(select(Document).where(Document.brand_id == brand.id)).all())
            logger.info(f"  {brand_name}: {doc_count} documents")
    session.close()


if __name__ == "__main__":
    asyncio.run(main())
