#!/usr/bin/env python3
"""
Allen & Heath Support Center Ingestion
Uses Zendesk API to extract all support documentation
Direct API access - no scraping, no Cloudflare issues
"""

import asyncio
import logging
import json
from typing import Optional, Set, Dict, List
import httpx
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document
from sqlmodel import select
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_ah_support.log")
    ]
)
logger = logging.getLogger("AH-Support-Center")

# Zendesk API endpoints
ZENDESK_DOMAIN = "allen-heath"
ZENDESK_API = f"https://{ZENDESK_DOMAIN}.zendesk.com/api/v2"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class AHSupportCenterIngestion:
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.ingested_articles: Set[int] = set()
        self.new_documents: int = 0
        self.failed_articles: Set[int] = set()
    
    async def initialize(self):
        """Start HTTP session"""
        self.session = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30
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
        """Load already-ingested support articles"""
        with Session(engine) as session:
            docs = session.exec(
                select(Document).where(
                    (Document.brand_id == brand_id) & 
                    (Document.url.like("%zendesk%"))
                )
            ).all()
            # Extract article IDs from URLs
            for doc in docs:
                if "articles/" in doc.url:
                    try:
                        article_id = int(doc.url.split("articles/")[-1].split("-")[0])
                        self.ingested_articles.add(article_id)
                    except:
                        pass
            logger.info(f"Already ingested: {len(self.ingested_articles)} support articles")
    
    async def fetch_json(self, endpoint: str) -> Optional[dict]:
        """Fetch JSON from Zendesk API"""
        try:
            url = f"{ZENDESK_API}/{endpoint}"
            logger.debug(f"Fetching: {url}")
            response = await self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"  → Status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"  → Error: {str(e)[:80]}")
            return None
    
    async def get_all_articles(self) -> List[Dict]:
        """Fetch all help center articles"""
        logger.info("\n" + "="*70)
        logger.info("FETCHING ARTICLES FROM ZENDESK API")
        logger.info("="*70)
        
        articles = []
        page = 1
        per_page = 100
        
        while True:
            logger.info(f"Fetching articles page {page}...")
            
            data = await self.fetch_json(
                f"help_center/articles.json?per_page={per_page}&page={page}&sort_by=created_at"
            )
            
            if not data or "articles" not in data:
                logger.warning("No articles found or API error")
                break
            
            batch = data.get("articles", [])
            if not batch:
                break
            
            articles.extend(batch)
            logger.info(f"  → Got {len(batch)} articles")
            
            # Check if there are more pages
            if not data.get("meta", {}).get("has_more"):
                break
            
            page += 1
            await asyncio.sleep(1)  # Be polite
        
        logger.info(f"✓ Fetched {len(articles)} total articles")
        return articles
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style
            for tag in soup(['script', 'style']):
                tag.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        except:
            return html
    
    async def ingest_articles(self, brand: Brand, articles: List[Dict]):
        """Ingest all articles into database"""
        logger.info("\n" + "="*70)
        logger.info("INGESTING ARTICLES")
        logger.info("="*70)
        
        # Filter to new articles only
        new_articles = [
            a for a in articles 
            if a.get("id") not in self.ingested_articles
        ]
        
        logger.info(f"New articles to ingest: {len(new_articles)}")
        
        if not new_articles:
            logger.info("No new articles to ingest")
            return
        
        # Ingest in batches
        batch_size = 10
        for i in range(0, len(new_articles), batch_size):
            batch = new_articles[i:i + batch_size]
            logger.info(f"\nBatch {i//batch_size + 1}/{(len(new_articles)-1)//batch_size + 1} ({len(batch)} articles)")
            
            for article in batch:
                try:
                    article_id = article.get("id")
                    title = article.get("title", "Untitled").strip()
                    
                    # Get full article content
                    full_data = await self.fetch_json(f"help_center/articles/{article_id}.json")
                    if not full_data or "article" not in full_data:
                        logger.warning(f"  ✗ Could not fetch article {article_id}")
                        self.failed_articles.add(article_id)
                        continue
                    
                    full_article = full_data["article"]
                    
                    # Extract content
                    content_html = full_article.get("body", "")
                    content = self._clean_html(content_html)
                    
                    if not content or len(content) < 50:
                        logger.info(f"  → Skipped (too short)")
                        continue
                    
                    # Build URL
                    article_url = full_article.get("html_url", 
                        f"https://support.allen-heath.com/hc/en-us/articles/{article_id}")
                    
                    # Ingest to SQL
                    with Session(engine) as session:
                        doc = Document(
                            brand_id=brand.id,
                            title=title,
                            content=content,
                            url=article_url
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
                                "source": article_url,
                                "title": title,
                                "brand_id": brand.id,
                                "brand": "Allen & Heath",
                                "doc_id": doc_id,
                                "type": "support_article",
                                "article_id": article_id
                            }
                        )
                    except Exception as e:
                        logger.warning(f"  ⚠ Vector DB: {str(e)[:50]}")
                    
                    self.new_documents += 1
                    self.ingested_articles.add(article_id)
                    logger.info(f"  ✓ Ingested: {title[:60]}")
                    
                except Exception as e:
                    logger.error(f"  ✗ Error: {str(e)[:80]}")
                    self.failed_articles.add(article.get("id"))
                
                await asyncio.sleep(0.2)  # Be polite
            
            if i + batch_size < len(new_articles):
                await asyncio.sleep(2)  # Delay between batches
    
    async def run(self):
        """Main workflow"""
        try:
            logger.info("="*70)
            logger.info("ALLEN & HEATH SUPPORT CENTER INGESTION")
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
            
            # Fetch articles from Zendesk API
            articles = await self.get_all_articles()
            
            if not articles:
                logger.error("Could not fetch articles from Zendesk API")
                logger.info("Trying alternative approach...")
                # Could fall back to web scraping here if API fails
                return
            
            # Ingest articles
            await self.ingest_articles(brand, articles)
            
            # Summary
            with Session(engine) as session:
                docs = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                
                logger.info("\n" + "="*70)
                logger.info("SUMMARY")
                logger.info("="*70)
                logger.info(f"Total AH documents now: {len(docs)}")
                logger.info(f"Support articles added: {self.new_documents}")
                logger.info(f"Failed articles: {len(self.failed_articles)}")
                logger.info(f"Coverage: {min(100, (len(docs)/500)*100):.1f}%")
                logger.info("="*70)
        
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.cleanup()


async def main():
    ingestion = AHSupportCenterIngestion()
    await ingestion.run()


if __name__ == "__main__":
    asyncio.run(main())
