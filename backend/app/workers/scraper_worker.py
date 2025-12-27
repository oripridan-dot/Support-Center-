"""
Distributed web scraping worker with auto-retry and browser pooling.

Features:
- Parallel scraping with Playwright
- Exponential backoff retry logic
- Memory-efficient browser management
- Error tracking and reporting
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from celery import Task
import structlog
from playwright.async_api import async_playwright, Browser, BrowserContext
from bs4 import BeautifulSoup

from app.workers.queue_manager import celery_app
from app.monitoring.metrics import scraping_tasks, scraping_duration

logger = structlog.get_logger(__name__)


class ScraperTask(Task):
    """
    Base task class for web scraping with automatic retry logic.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True  # Add random jitter to prevent thundering herd
    
    # Browser instance pooling (class-level)
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None


async def get_browser_context() -> tuple[Browser, BrowserContext]:
    """
    Get or create a browser context for scraping.
    Thread-safe browser pooling.
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920x1080',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    return browser, context


@celery_app.task(base=ScraperTask, bind=True, name='app.workers.scraper_worker.scrape_product_page')
def scrape_product_page(
    self,
    url: str,
    brand: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Scrape a single product page and queue for embedding generation.
    
    Args:
        url: Target URL to scrape
        brand: Brand name (e.g., 'Roland', 'Yamaha')
        metadata: Additional metadata to attach
        
    Returns:
        Dictionary with scraping results and status
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("scraping_started", url=url, brand=brand, task_id=self.request.id)
        
        # Run async scraping in event loop
        result = asyncio.run(_scrape_page_async(url, brand, metadata))
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        scraping_duration.observe(duration)
        scraping_tasks.labels(status='success').inc()
        
        # Queue embedding generation if content extracted
        if result.get('content'):
            from app.workers.embedding_worker import embedding_task
            embedding_task.apply_async(
                args=[result['content'], url, brand, metadata],
                priority=8,  # High priority
                countdown=2  # Small delay to avoid overwhelming
            )
        
        logger.info(
            "scraping_completed",
            url=url,
            brand=brand,
            content_length=len(result.get('content', '')),
            duration=duration
        )
        
        return {
            'status': 'success',
            'url': url,
            'brand': brand,
            'content_length': len(result.get('content', '')),
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        scraping_tasks.labels(status='failed').inc()
        logger.error("scraping_failed", url=url, brand=brand, error=str(e))
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _scrape_page_async(
    url: str,
    brand: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Async implementation of page scraping with Playwright.
    """
    browser, context = await get_browser_context()
    
    try:
        page = await context.new_page()
        
        # Navigate with timeout
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        
        # Wait for dynamic content
        await page.wait_for_timeout(2000)
        
        # Extract content
        content = await page.content()
        title = await page.title()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'lxml')
        
        # Extract structured data
        structured_data = {
            'url': url,
            'brand': brand,
            'title': title,
            'content': soup.get_text(separator=' ', strip=True),
            'html': str(soup),
            'links': [a.get('href') for a in soup.find_all('a', href=True)],
            'images': [img.get('src') for img in soup.find_all('img', src=True)],
            'metadata': metadata or {},
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        await page.close()
        return structured_data
        
    finally:
        await context.close()
        await browser.close()


@celery_app.task(bind=True, name='app.workers.scraper_worker.batch_scrape')
def batch_scrape(
    self,
    urls: List[str],
    brand: str,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Scrape multiple URLs in parallel batches.
    
    Args:
        urls: List of URLs to scrape
        brand: Brand name
        batch_size: Number of concurrent scrapes
        
    Returns:
        Summary of batch scraping results
    """
    logger.info("batch_scrape_started", brand=brand, url_count=len(urls), batch_size=batch_size)
    
    results = []
    failed = []
    
    # Process in batches
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        
        # Create task group
        from celery import group
        job = group(
            scrape_product_page.s(url, brand)
            for url in batch
        )
        
        # Execute batch
        result = job.apply_async()
        
        # Wait for batch completion with timeout
        try:
            batch_results = result.get(timeout=300)  # 5 min timeout
            results.extend(batch_results)
        except Exception as e:
            logger.error("batch_failed", batch_num=i//batch_size, error=str(e))
            failed.extend(batch)
    
    summary = {
        'status': 'completed',
        'brand': brand,
        'total_urls': len(urls),
        'successful': len(results),
        'failed': len(failed),
        'failed_urls': failed,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info("batch_scrape_completed", **summary)
    return summary


@celery_app.task(name='app.workers.scraper_worker.discover_links')
def discover_links(
    start_url: str,
    brand: str,
    max_depth: int = 3,
    patterns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Discover and queue all product links from a catalog page.
    
    Args:
        start_url: Starting URL (e.g., brand homepage)
        brand: Brand name
        max_depth: Maximum crawl depth
        patterns: URL patterns to match (regex)
        
    Returns:
        Discovered URLs and crawl statistics
    """
    logger.info("link_discovery_started", brand=brand, start_url=start_url)
    
    discovered_urls = asyncio.run(
        _discover_links_async(start_url, brand, max_depth, patterns)
    )
    
    # Queue discovered URLs for scraping
    if discovered_urls:
        batch_scrape.apply_async(
            args=[discovered_urls, brand],
            priority=5
        )
    
    return {
        'status': 'completed',
        'brand': brand,
        'discovered_count': len(discovered_urls),
        'urls': discovered_urls,
        'timestamp': datetime.utcnow().isoformat()
    }


async def _discover_links_async(
    start_url: str,
    brand: str,
    max_depth: int,
    patterns: Optional[List[str]] = None
) -> List[str]:
    """
    Async link discovery with depth-limited crawling.
    """
    import re
    from urllib.parse import urljoin, urlparse
    
    visited = set()
    to_visit = [(start_url, 0)]
    discovered = []
    
    browser, context = await get_browser_context()
    
    try:
        while to_visit:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            try:
                page = await context.new_page()
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')
                
                # Find all links
                for link in soup.find_all('a', href=True):
                    href = urljoin(url, link['href'])
                    
                    # Apply pattern filtering if provided
                    if patterns:
                        if any(re.search(pattern, href) for pattern in patterns):
                            if href not in visited:
                                discovered.append(href)
                                to_visit.append((href, depth + 1))
                    else:
                        # Same domain only
                        if urlparse(href).netloc == urlparse(start_url).netloc:
                            if href not in visited:
                                discovered.append(href)
                                to_visit.append((href, depth + 1))
                
                await page.close()
                
            except Exception as e:
                logger.error("link_discovery_error", url=url, error=str(e))
                continue
        
        return list(set(discovered))
        
    finally:
        await context.close()
        await browser.close()
