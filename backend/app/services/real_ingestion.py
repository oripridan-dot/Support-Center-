"""
REAL Ingestion Service - Actually scrapes and ingests brand documentation
Wired to HP 22-worker system for parallel processing
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from playwright.async_api import async_playwright

from app.core.database import get_session
from app.models.sql_models import Brand, Document
from app.scrapers.smart_scraper import SmartScraper
from app.services.ingestion_tracker import tracker

logger = logging.getLogger(__name__)


class RealIngestionService:
    """Real ingestion service that actually works"""
    
    def __init__(self):
        self.scraper = SmartScraper(
            max_concurrent=6,  # Match HP scraping workers
            delay_ms=500,
            timeout_ms=30000,
            max_retries=2
        )
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
    
    async def discover_brand_urls(self, brand_name: str, base_url: Optional[str] = None) -> List[str]:
        """
        Discover documentation URLs for a brand
        
        Priority:
        1. Check if scraped_docs.json exists
        2. Check if strategy file exists
        3. Try common support/documentation patterns
        """
        brand_dir = self.data_dir / brand_name.lower().replace(" ", "_")
        brand_dir.mkdir(exist_ok=True)
        
        # Check for existing scraped data
        scraped_file = brand_dir / "scraped_docs.json"
        if scraped_file.exists():
            try:
                with open(scraped_file, 'r') as f:
                    data = json.load(f)
                    docs = data.get('documents', [])
                    urls = [doc.get('url') for doc in docs if doc.get('url')]
                    if urls:
                        logger.info(f"Found {len(urls)} existing URLs for {brand_name}")
                        return urls
            except Exception as e:
                logger.warning(f"Failed to load scraped_docs.json for {brand_name}: {e}")
        
        # Check for strategy file
        strategy_file = self.data_dir / "strategies" / f"{brand_name.lower().replace(' ', '_')}_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, 'r') as f:
                    strategy = json.load(f)
                    urls = []
                    # Extract URLs from strategy
                    if 'documentation_urls' in strategy:
                        urls.extend(strategy['documentation_urls'])
                    if 'support_url' in strategy:
                        urls.append(strategy['support_url'])
                    if 'base_url' in strategy:
                        urls.append(strategy['base_url'])
                    if urls:
                        logger.info(f"Found {len(urls)} URLs in strategy for {brand_name}")
                        return urls
            except Exception as e:
                logger.warning(f"Failed to load strategy for {brand_name}: {e}")
        
        # If we have a base_url, try common patterns
        if base_url:
            common_paths = [
                "/support",
                "/support/documentation",
                "/support/manuals",
                "/support/downloads",
                "/docs",
                "/documentation",
                "/help",
                "/knowledge-base",
                "/resources"
            ]
            urls = [f"{base_url.rstrip('/')}{path}" for path in common_paths]
            logger.info(f"Generated {len(urls)} potential URLs for {brand_name}")
            return urls
        
        logger.warning(f"No URLs found for {brand_name}")
        return []
    
    async def scrape_brand(
        self, 
        brand_name: str, 
        session: Session,
        force_rescan: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape and ingest a brand's documentation
        
        Returns:
            Dict with status and statistics
        """
        logger.info(f"Starting REAL scraping for {brand_name}")
        
        # Update tracker - start ingestion
        tracker.start(brand_name)
        
        try:
            # Get brand from DB
            brand = session.exec(
                select(Brand).where(Brand.name == brand_name)
            ).first()
            
            if not brand:
                error_msg = f"Brand {brand_name} not found in database"
                logger.error(error_msg)
                tracker.add_error(error_msg)
                tracker.complete()
                raise ValueError(error_msg)
            
            # Discover URLs
            tracker.update_step("Discovering URLs", brand_name)
            base_url = brand.website_url
            urls = await self.discover_brand_urls(brand_name, base_url)
            
            if not urls:
                error_msg = "No URLs found"
                logger.error(f"{error_msg} for {brand_name}")
                tracker.add_error(error_msg)
                tracker.complete()
                return {
                    "success": False,
                    "error": error_msg,
                    "brand": brand_name,
                    "urls_found": 0
                }
            
            tracker.update_urls(discovered=len(urls), processed=0, brand_name=brand_name)
            logger.info(f"Discovered {len(urls)} URLs for {brand_name}")
            
            # Scrape all URLs
            tracker.update_step("Scraping pages", brand_name)
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                
                results = []
                for i, url in enumerate(urls):
                    # Handle URL as string or dict
                    url_str = url if isinstance(url, str) else url.get('url', str(url))
                    tracker.update_step(f"Scraping {i+1}/{len(urls)}: {url_str[:50]}...", brand_name)
                    tracker.update_urls(discovered=len(urls), processed=i + 1, brand_name=brand_name)
                    
                    result = await self.scraper.scrape_page(url_str, browser)
                    results.append(result)
                    
                    # If successful, save to database
                    if result.success and result.content:
                        await self._save_document(
                            session=session,
                            brand=brand,
                            url=url_str,
                            content=result.content,
                            title=self._extract_title(result.content)
                        )
                        tracker.update_document_count(brand_name, i + 1)
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.5)
                
                await browser.close()
            
            # Calculate statistics
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            
            # Save scraped data to file
            self._save_scraped_data(brand_name, results)
            
            # Update tracker - complete
            tracker.update_brand_complete(brand_name, successful)
            tracker.complete()
            
            logger.info(
                f"Completed scraping {brand_name}: "
                f"{successful} successful, {failed} failed"
            )
            
            return {
                "success": True,
                "brand": brand_name,
                "urls_found": len(urls),
                "urls_scraped": len(results),
                "successful": successful,
                "failed": failed,
                "documents_saved": successful
            }
            
        except Exception as e:
            logger.error(f"Error scraping {brand_name}: {e}", exc_info=True)
            tracker.add_error(str(e))
            tracker.complete()
            return {
                "success": False,
                "error": str(e),
                "brand": brand_name
            }
    
    async def _save_document(
        self,
        session: Session,
        brand: Brand,
        url: str,
        content: str,
        title: str
    ):
        """Save a document to the database"""
        try:
            # Check if document already exists
            existing = session.exec(
                select(Document).where(
                    Document.brand_id == brand.id,
                    Document.url == url
                )
            ).first()
            
            if existing:
                # Update existing
                existing.content = content
                existing.title = title
                existing.last_updated = datetime.utcnow()
                logger.info(f"Updated document: {url}")
            else:
                # Create new
                doc = Document(
                    brand_id=brand.id,
                    title=title,
                    content=content,
                    url=url,
                    doc_type="web_page",
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                session.add(doc)
                logger.info(f"Created document: {url}")
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save document {url}: {e}")
            session.rollback()
    
    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML content"""
        try:
            # Simple title extraction
            if "<title>" in html_content:
                start = html_content.find("<title>") + 7
                end = html_content.find("</title>", start)
                return html_content[start:end].strip()
        except:
            pass
        return "Untitled Document"
    
    def _save_scraped_data(self, brand_name: str, results: List[Any]):
        """Save scraped data to JSON file for backup"""
        try:
            brand_dir = self.data_dir / brand_name.lower().replace(" ", "_")
            brand_dir.mkdir(exist_ok=True)
            
            output_file = brand_dir / "scraped_docs.json"
            
            data = {
                "brand_name": brand_name,
                "scraped_at": datetime.utcnow().isoformat(),
                "documents": [
                    {
                        "url": r.url,
                        "success": r.success,
                        "status_code": r.status_code,
                        "error": r.error,
                        "content_length": len(r.content) if r.content else 0
                    }
                    for r in results
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved scraped data to {output_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save scraped data: {e}")


# Global instance
real_ingestion_service = RealIngestionService()
