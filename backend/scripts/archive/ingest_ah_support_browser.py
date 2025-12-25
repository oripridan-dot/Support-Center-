#!/usr/bin/env python3
"""
Allen & Heath Support Center - Browser-Based Ingestion
Uses Playwright with better anti-detection for support.allen-heath.com
"""

import asyncio
import logging
import re
from typing import Optional, Set, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_support_browser.log")
    ]
)
logger = logging.getLogger("AH-Support-Browser")


class AHSupportBrowserIngestion:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.ingested_articles: Set[int] = set()
        self.discovered_urls: Set[str] = set()
        self.new_documents: int = 0
        self.failed_urls: Set[str] = set()
    
    async def start(self):
        """Initialize browser"""
        logger.info("Initializing browser...")
        self.playwright = await async_playwright().start()
        
        # Use chromium with aggressive anti-detection
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        
        logger.info("✓ Browser initialized")
    
    async def stop(self):
        """Clean up browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()
    
    def _get_ah_brand(self) -> Optional[Brand]:
        """Get Allen & Heath brand"""
        with Session(engine) as session:
            return session.exec(
                select(Brand).where(Brand.name == "Allen & Heath")
            ).first()
    
    def _load_ingested(self, brand_id: int):
        """Load already-ingested support articles"""
        with Session(engine) as session:
            docs = session.exec(
                select(Document).where(
                    (Document.brand_id == brand_id) & 
                    (Document.url.like("%support.allen-heath%"))
                )
            ).all()
            self.ingested_articles = {
                int(doc.url.split("/articles/")[-1].split("-")[0]) 
                for doc in docs 
                if "/articles/" in doc.url
            }
            logger.info(f"Already ingested: {len(self.ingested_articles)} support articles")
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page with browser"""
        page = None
        try:
            logger.info(f"Fetching: {url}")
            page = await self.context.new_page()
            
            # Navigate with long timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Check for Cloudflare block
            content = await page.content()
            if "Just a moment" in content:
                logger.warning(f"  → Cloudflare block detected")
                return None
            
            logger.info(f"  ✓ Loaded successfully")
            return content
            
        except Exception as e:
            logger.warning(f"  → Error: {str(e)[:80]}")
            return None
        finally:
            if page:
                await page.close()
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines[:5000])
        except:
            return ""
    
    def _extract_article_id(self, url: str) -> Optional[int]:
        """Extract article ID from URL"""
        try:
            match = re.search(r'/articles/(\d+)', url)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    async def discover_articles(self) -> Set[str]:
        """Discover all support articles"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 1: DISCOVERING SUPPORT ARTICLES")
        logger.info("="*70)
        
        # Start from main support page
        main_url = "https://support.allen-heath.com/hc/en-us"
        html = await self.fetch_page(main_url)
        
        if not html:
            logger.error("Could not fetch main support page")
            return set()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all article links
        article_links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Look for article URLs
            if '/articles/' in href:
                full_url = urljoin(main_url, href)
                full_url = full_url.split('#')[0]
                article_links.add(full_url)
                logger.debug(f"  → Found article: {full_url}")
        
        logger.info(f"✓ Discovered {len(article_links)} article links on main page")
        
        # Also try to find category pages and crawl those
        category_links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/sections/' in href or '/categories/' in href:
                full_url = urljoin(main_url, href)
                category_links.add(full_url)
        
        logger.info(f"Found {len(category_links)} category pages to explore")
        
        # Crawl a few category pages
        for i, cat_url in enumerate(list(category_links)[:5]):
            logger.info(f"  Exploring category {i+1}/5: {cat_url.split('/')[-1]}")
            
            cat_html = await self.fetch_page(cat_url)
            if not cat_html:
                continue
            
            cat_soup = BeautifulSoup(cat_html, 'html.parser')
            for link in cat_soup.find_all('a', href=True):
                href = link['href']
                if '/articles/' in href:
                    full_url = urljoin(main_url, href)
                    full_url = full_url.split('#')[0]
                    article_links.add(full_url)
            
            await asyncio.sleep(1)  # Be polite
        
        logger.info(f"✓ Total articles discovered: {len(article_links)}")
        return article_links
    
    async def ingest_articles(self, brand: Brand, article_urls: Set[str]):
        """Ingest articles"""
        logger.info("\n" + "="*70)
        logger.info("PHASE 2: INGESTING ARTICLES")
        logger.info("="*70)
        
        # Filter to new articles
        new_urls = [
            url for url in article_urls
            if self._extract_article_id(url) not in self.ingested_articles
        ]
        
        logger.info(f"New articles to ingest: {len(new_urls)}")
        
        if not new_urls:
            logger.info("No new articles")
            return
        
        # Ingest in batches
        batch_size = 5
        for i in range(0, len(new_urls), batch_size):
            batch = new_urls[i:i + batch_size]
            logger.info(f"\nBatch {i//batch_size + 1}/{(len(new_urls)-1)//batch_size + 1}")
            
            for url in batch:
                try:
                    # Fetch article
                    html = await self.fetch_page(url)
                    if not html:
                        self.failed_urls.add(url)
                        continue
                    
                    # Parse article
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('h1')
                    title = title_tag.get_text(strip=True) if title_tag else "Untitled"
                    
                    # Extract content
                    article_body = soup.find('article') or soup.find('div', class_='article')
                    if not article_body:
                        logger.info(f"  → Skipped (no article body)")
                        continue
                    
                    content = self._extract_text(str(article_body))
                    if not content or len(content) < 50:
                        logger.info(f"  → Skipped (too short)")
                        continue
                    
                    # Ingest to SQL
                    with Session(engine) as session:
                        doc = Document(
                            brand_id=brand.id,
                            title=title,
                            content=content,
                            url=url
                        )
                        session.add(doc)
                        session.commit()
                        session.refresh(doc)
                        doc_id = doc.id
                    
                    # Ingest to ChromaDB
                    try:
                        await ingest_document(
                            text=content,
                            metadata={
                                "source": url,
                                "title": title,
                                "brand_id": brand.id,
                                "brand": "Allen & Heath",
                                "doc_id": doc_id,
                                "type": "support_article"
                            }
                        )
                    except Exception as e:
                        logger.warning(f"  ⚠ Vector DB: {str(e)[:50]}")
                    
                    self.new_documents += 1
                    article_id = self._extract_article_id(url)
                    if article_id:
                        self.ingested_articles.add(article_id)
                    
                    logger.info(f"  ✓ Ingested: {title[:60]}")
                    
                except Exception as e:
                    logger.error(f"  ✗ Error: {str(e)[:80]}")
                    self.failed_urls.add(url)
                
                await asyncio.sleep(1)  # Be very polite
            
            if i + batch_size < len(new_urls):
                await asyncio.sleep(3)
    
    async def run(self):
        """Main workflow"""
        try:
            logger.info("="*70)
            logger.info("ALLEN & HEATH SUPPORT CENTER INGESTION (Browser)")
            logger.info("="*70)
            
            await self.start()
            
            brand = self._get_ah_brand()
            if not brand:
                logger.error("Allen & Heath brand not found!")
                return
            
            self._load_ingested(brand.id)
            
            # Discover articles
            article_urls = await self.discover_articles()
            
            if not article_urls:
                logger.error("Could not discover any articles")
                return
            
            # Ingest articles
            await self.ingest_articles(brand, article_urls)
            
            # Summary
            with Session(engine) as session:
                docs = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                
                logger.info("\n" + "="*70)
                logger.info("SUMMARY")
                logger.info("="*70)
                logger.info(f"Total AH documents: {len(docs)}")
                logger.info(f"Support articles added: {self.new_documents}")
                logger.info(f"Failed articles: {len(self.failed_urls)}")
                logger.info("="*70)
        
        finally:
            await self.stop()


async def main():
    ingestion = AHSupportBrowserIngestion()
    await ingestion.run()


if __name__ == "__main__":
    asyncio.run(main())
