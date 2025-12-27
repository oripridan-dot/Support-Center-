"""
Scraper Worker

Responsibilities:
- Receives scraping instructions from Explorer
- Executes document extraction based on strategy
- Handles various content types (PDFs, HTML, images)
- Respects rate limits and anti-bot measures
- Passes extracted content to Ingester

The Scraper is the execution layer that follows Explorer's instructions
to collect all documentation efficiently and reliably.
"""

import asyncio
import os
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.workers.explorer import ScrapingStrategy, DocumentationSource


class ScrapedDocument(BaseModel):
    """Represents a scraped document ready for ingestion"""
    url: str
    title: str
    content: str
    doc_type: str
    brand_id: int
    brand_name: str
    file_path: Optional[str] = None
    metadata: Dict = {}
    scraped_at: datetime


class ScraperWorker:
    """
    Executes scraping based on Explorer's strategy.
    
    MISSION: Execute the Explorer's instructions with 100% accuracy.
    Persistent, thorough, and doesn't skip a single document.
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.retry_count: int = 3  # Retry failed downloads
        self.failed_urls: List[str] = []  # Track failures for reporting
    
    async def initialize(self):
        """Initialize browser and HTTP session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.session = aiohttp.ClientSession()
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.session:
            await self.session.close()
    
    async def execute_strategy(self, strategy: ScrapingStrategy) -> List[ScrapedDocument]:
        """
        Main scraping method - follows Explorer's instructions
        """
        print(f"🤖 [SCRAPER] Starting scraping for {strategy.brand_name}")
        print(f"  🎯 Target: {strategy.total_estimated_docs} documents")
        print(f"  📄 URLs to process: {len(strategy.documentation_urls)}")
        print(f"  🔄 Retry policy: {self.retry_count}x attempts per document\n")
        
        # Update status tracker
        from app.workers.status_tracker import worker_status
        worker_status.scraper_start(strategy.brand_id, strategy.brand_name, strategy.total_estimated_docs)
        
        if not self.browser:
            await self.initialize()
        
        # Check for already-scraped documents
        from app.core.database import get_session
        from app.models.sql_models import Document
        from sqlmodel import select
        
        session = next(get_session())
        existing_urls = set()
        try:
            existing_docs = session.exec(
                select(Document.url).where(Document.brand_id == strategy.brand_id)
            ).all()
            existing_urls = set(existing_docs)
            if existing_urls:
                print(f"  ℹ️  Found {len(existing_urls)} already-scraped documents")
        finally:
            session.close()
        
        scraped_docs: List[ScrapedDocument] = []
        self.failed_urls = []
        skipped_count = 0
        
        for idx, doc_source in enumerate(strategy.documentation_urls, 1):
            # Skip if already scraped
            if doc_source.url in existing_urls:
                print(f"  [{idx}/{len(strategy.documentation_urls)}] ⏭️  Already scraped: {doc_source.title or doc_source.url[:50]}")
                skipped_count += 1
                continue
            
            success = False
            attempts = 0
            
            # Update status with current document
            from app.workers.status_tracker import worker_status
            worker_status._log(f"🤖 Scraping: {doc_source.title or doc_source.url[:50]}...")
            
            while not success and attempts < self.retry_count:
                attempts += 1
                try:
                    print(f"  [{idx}/{len(strategy.documentation_urls)}] {'Retry ' + str(attempts) + ' - ' if attempts > 1 else ''}Scraping: {doc_source.title or doc_source.url}")
                    
                    # Rate limiting
                    if idx > 1 or attempts > 1:
                        await asyncio.sleep(strategy.rate_limit_ms / 1000)
                    
                    # Route to appropriate scraper based on content type
                    if doc_source.url.endswith('.pdf'):
                        doc = await self._scrape_pdf(doc_source, strategy)
                    else:
                        doc = await self._scrape_html(doc_source, strategy)
                    
                    if doc:
                        scraped_docs.append(doc)
                        print(f"    ✅ SUCCESS: {doc.title} ({len(doc.content)} chars)")
                        worker_status._log(f"✅ Scraped: {doc.title} ({len(doc.content)} chars)")
                        success = True
                        
                        # Update progress
                        progress = int((len(scraped_docs) / strategy.total_estimated_docs) * 100)
                        worker_status.scraper_progress(
                            f"Scraped {len(scraped_docs)}/{strategy.total_estimated_docs} docs",
                            progress,
                            len(scraped_docs)
                        )
                    
                except asyncio.TimeoutError:
                    if attempts >= self.retry_count:
                        print(f"    ⏱️  TIMEOUT after {attempts} attempts - skipping")
                        self.failed_urls.append(doc_source.url)
                    else:
                        print(f"    ⏱️  Attempt {attempts} timed out, retrying...")
                    continue
                except Exception as e:
                    if attempts >= self.retry_count:
                        print(f"    ❌ FAILED after {attempts} attempts: {e}")
                        self.failed_urls.append(doc_source.url)
                    else:
                        print(f"    ⚠️  Attempt {attempts} failed, retrying... ({e})")
                    continue
        
        success_rate = (len(scraped_docs) / len(strategy.documentation_urls) * 100) if strategy.documentation_urls else 0
        
        print(f"\n{'='*70}")
        print(f"📊 SCRAPING REPORT: {strategy.brand_name}")
        print(f"{'='*70}")
        print(f"✅ SCRAPED:    {len(scraped_docs)} new documents")
        print(f"⏭️  SKIPPED:    {skipped_count} already-scraped documents")
        print(f"📝 TOTAL:      {len(strategy.documentation_urls)} URLs processed")
        print(f"📈 SUCCESS:    {success_rate:.1f}%")
        
        if self.failed_urls:
            print(f"❌ FAILED:     {len(self.failed_urls)} documents")
            print(f"\n🔴 Failed URLs (needs manual review):")
            for url in self.failed_urls[:10]:  # Show first 10
                print(f"   • {url}")
            if len(self.failed_urls) > 10:
                print(f"   ... and {len(self.failed_urls) - 10} more")
            
            # Log failures
            self._log_failures(strategy.brand_name)
        else:
            if skipped_count > 0:
                print(f"✅ All URLs processed ({skipped_count} already existed)")
            else:
                print(f"🎉 100% SCRAPING SUCCESS!")
        
        print(f"{'='*70}\n")
        
        # Update status tracker
        from app.workers.status_tracker import worker_status
        worker_status.scraper_complete(len(scraped_docs), len(self.failed_urls))
        
        return scraped_docs
    
    def _log_failures(self, brand_name: str):
        """Log failed URLs for manual follow-up"""
        failure_file = f"/workspaces/Support-Center-/backend/data/{brand_name.lower().replace(' ', '_')}/scraping_failures.txt"
        import os
        os.makedirs(os.path.dirname(failure_file), exist_ok=True)
        
        with open(failure_file, 'w') as f:
            f.write(f"# SCRAPING FAILURES FOR {brand_name}\n")
            f.write(f"# Generated: {datetime.now()}\n\n")
            for url in self.failed_urls:
                f.write(f"{url}\n")
        
        print(f"  💾 Failures logged to: {failure_file}")
    
    async def _scrape_pdf(self, source: DocumentationSource, strategy: ScrapingStrategy) -> Optional[ScrapedDocument]:
        """
        Download and extract text from PDF
        """
        try:
            # Download PDF
            async with self.session.get(source.url, timeout=30) as response:
                if response.status != 200:
                    print(f"    ⚠️  HTTP {response.status} for {source.url}")
                    return None
                
                pdf_content = await response.read()
            
            # Save PDF to disk
            brand_dir = f"/workspaces/Support-Center-/backend/data/{strategy.brand_name.lower().replace(' ', '_')}"
            os.makedirs(brand_dir, exist_ok=True)
            
            # Generate filename from URL
            url_hash = hashlib.md5(source.url.encode()).hexdigest()[:8]
            filename = f"{source.title or 'document'}_{url_hash}.pdf".replace('/', '_').replace(' ', '_')
            file_path = os.path.join(brand_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            
            # Extract text from PDF (basic implementation)
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except Exception as e:
                print(f"    ⚠️  PDF text extraction failed: {e}")
                text = f"[PDF Document: {source.title}]"
            
            return ScrapedDocument(
                url=source.url,
                title=source.title or "PDF Document",
                content=text,
                doc_type=source.type,
                brand_id=strategy.brand_id,
                brand_name=strategy.brand_name,
                file_path=file_path,
                scraped_at=datetime.now()
            )
        
        except Exception as e:
            print(f"    ❌ PDF scraping error: {e}")
            return None
    
    async def _scrape_html(self, source: DocumentationSource, strategy: ScrapingStrategy) -> Optional[ScrapedDocument]:
        """
        Scrape HTML documentation page
        """
        try:
            page = await self.browser.new_page()
            
            try:
                # Use domcontentloaded instead of networkidle - modern sites never idle
                # Product pages have analytics, chat widgets, etc that keep connections open
                await page.goto(source.url, wait_until="domcontentloaded", timeout=15000)
                
                # Wait a bit for dynamic content to load
                await asyncio.sleep(2)
                
                # Extract title
                title = source.title
                if not title:
                    title_elem = await page.query_selector(strategy.content_selectors.get('title', 'h1'))
                    if title_elem:
                        title = await title_elem.text_content()
                
                # Extract main content
                content_selector = strategy.content_selectors.get('content', 'article, main, .content')
                content_elem = await page.query_selector(content_selector)
                
                if content_elem:
                    html_content = await content_elem.inner_html()
                    # Parse with BeautifulSoup for clean text
                    soup = BeautifulSoup(html_content, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                else:
                    # Fallback to body
                    text = await page.text_content('body')
                
                # Save HTML to disk
                brand_dir = f"/workspaces/Support-Center-/backend/data/{strategy.brand_name.lower().replace(' ', '_')}"
                os.makedirs(brand_dir, exist_ok=True)
                
                url_hash = hashlib.md5(source.url.encode()).hexdigest()[:8]
                filename = f"{title or 'page'}_{url_hash}.html".replace('/', '_').replace(' ', '_')
                file_path = os.path.join(brand_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                return ScrapedDocument(
                    url=source.url,
                    title=title or "Documentation Page",
                    content=text,
                    doc_type=source.type,
                    brand_id=strategy.brand_id,
                    brand_name=strategy.brand_name,
                    file_path=file_path,
                    scraped_at=datetime.now()
                )
            
            finally:
                await page.close()
        
        except Exception as e:
            print(f"    ❌ HTML scraping error: {e}")
            return None
    
    def save_to_disk(self, docs: List[ScrapedDocument], strategy: ScrapingStrategy):
        """
        Save scraped documents metadata to JSON for handoff to Ingester
        """
        output_dir = f"/workspaces/Support-Center-/backend/data/{strategy.brand_name.lower().replace(' ', '_')}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, "scraped_docs.json")
        
        import json
        with open(output_file, 'w') as f:
            json.dump([doc.model_dump() for doc in docs], f, indent=2, default=str)
        
        print(f"  💾 Saved {len(docs)} documents to {output_file}")
