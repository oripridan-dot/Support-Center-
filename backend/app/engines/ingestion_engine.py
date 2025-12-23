import asyncio
import logging
import hashlib
import random
from typing import List, Optional, Any
from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Document, Product, Brand
from app.services.rag_service import ingest_document

logger = logging.getLogger(__name__)

class IngestionEngine:
    def __init__(self, scraper: BaseScraper):
        self.scraper = scraper

    def get_content_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    async def process_url(self, url: str, brand_id: int, product_id: Optional[int] = None):
        logger.info(f"Processing URL: {url}")
        
        content = await self.scraper.scrape_url(url)
        if not content:
            logger.warning(f"Failed to get content for {url}")
            return False

        soup = BeautifulSoup(content, 'html.parser')
        
        # Basic extraction - can be refined per brand
        title = soup.title.string if soup.title else url
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)
        
        content_hash = self.get_content_hash(text)

        with Session(engine) as session:
            # Check if document already exists and hasn't changed
            existing_doc = session.exec(
                select(Document).where(Document.url == url)
            ).first()

            if existing_doc and existing_doc.content_hash == content_hash:
                logger.info(f"Document {url} is up to date.")
                return True

            if existing_doc:
                logger.info(f"Updating document: {url}")
                existing_doc.title = title
                existing_doc.content_hash = content_hash
                doc = existing_doc
            else:
                logger.info(f"Creating new document: {url}")
                doc = Document(
                    title=title,
                    url=url,
                    content_hash=content_hash,
                    brand_id=brand_id,
                    product_id=product_id
                )
                session.add(doc)
            
            session.commit()
            session.refresh(doc)

            # Update Vector DB
            try:
                await ingest_document(
                    text=text,
                    metadata={
                        "source": url,
                        "title": str(title),
                        "brand_id": int(brand_id),
                        "product_id": int(product_id) if product_id else 0,
                        "doc_id": int(doc.id)
                    }
                )
                logger.info(f"Ingested {url} into Vector DB")
            except Exception as e:
                logger.error(f"Failed to ingest into Vector DB: {e}")

        return True

    async def run_ingestion(self, urls: List[str], brand_id: int):
        logger.info(f"Starting ingestion for {len(urls)} URLs")
        results = []
        for url in urls:
            success = await self.process_url(url, brand_id)
            results.append(success)
            # Adaptive delay
            await asyncio.sleep(random.uniform(5, 15))
        return results
