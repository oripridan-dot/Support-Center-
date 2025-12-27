"""
Smart Scraper - Parallel scraping with rate limiting and retry logic
Dramatically improves scraping throughput while respecting server limits
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
import logging
from playwright.async_api import async_playwright, Browser, Page
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result from a single scraping operation"""
    url: str
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class SmartScraper:
    """
    Parallel scraping with intelligent rate limiting
    
    Features:
    - Concurrent scraping with semaphore control
    - Automatic retry with exponential backoff
    - Rate limiting to avoid server overload
    - Detailed success/failure tracking
    """
    
    def __init__(
        self, 
        max_concurrent: int = 5, 
        delay_ms: int = 1000,
        timeout_ms: int = 30000,
        max_retries: int = 3
    ):
        """
        Initialize scraper
        
        Args:
            max_concurrent: Maximum concurrent requests
            delay_ms: Delay between requests in milliseconds
            timeout_ms: Request timeout in milliseconds
            max_retries: Maximum retry attempts per URL
        """
        self.max_concurrent = max_concurrent
        self.delay_ms = delay_ms
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(
            f"SmartScraper initialized: concurrent={max_concurrent}, "
            f"delay={delay_ms}ms, timeout={timeout_ms}ms"
        )
    
    async def scrape_page(
        self, 
        url: str, 
        browser: Browser,
        wait_for_selector: Optional[str] = None
    ) -> ScrapingResult:
        """
        Scrape single page with retry logic
        
        Args:
            url: URL to scrape
            browser: Playwright browser instance
            wait_for_selector: Optional CSS selector to wait for
            
        Returns:
            ScrapingResult with content or error
        """
        async with self.semaphore:  # Rate limiting
            start_time = asyncio.get_event_loop().time()
            
            for attempt in range(self.max_retries):
                page: Optional[Page] = None
                
                try:
                    page = await browser.new_page()
                    
                    # Navigate to URL
                    response = await page.goto(url, timeout=self.timeout_ms)
                    
                    # Wait for specific selector if provided
                    if wait_for_selector:
                        await page.wait_for_selector(
                            wait_for_selector, 
                            timeout=self.timeout_ms
                        )
                    
                    # Get page content
                    content = await page.content()
                    
                    # Calculate duration
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    
                    await page.close()
                    
                    # Rate limit delay
                    await asyncio.sleep(self.delay_ms / 1000)
                    
                    logger.info(f"✓ Scraped: {url} ({duration_ms:.0f}ms)")
                    
                    return ScrapingResult(
                        url=url,
                        success=True,
                        content=content,
                        status_code=response.status if response else None,
                        duration_ms=duration_ms
                    )
                    
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {self.timeout_ms}ms"
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} - {url}: {error_msg}"
                    )
                    
                    if page:
                        await page.close()
                    
                    if attempt == self.max_retries - 1:  # Last attempt
                        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                        return ScrapingResult(
                            url=url,
                            success=False,
                            error=error_msg,
                            duration_ms=duration_ms
                        )
                    
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} - {url}: {error_msg}"
                    )
                    
                    if page:
                        await page.close()
                    
                    if attempt == self.max_retries - 1:  # Last attempt
                        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                        return ScrapingResult(
                            url=url,
                            success=False,
                            error=error_msg,
                            duration_ms=duration_ms
                        )
                    
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
    
    async def scrape_batch(
        self, 
        urls: List[str],
        wait_for_selector: Optional[str] = None
    ) -> List[ScrapingResult]:
        """
        Scrape multiple URLs in parallel
        
        Args:
            urls: List of URLs to scrape
            wait_for_selector: Optional CSS selector to wait for
            
        Returns:
            List of ScrapingResults
        """
        logger.info(f"Starting batch scrape: {len(urls)} URLs")
        start_time = asyncio.get_event_loop().time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                # Create tasks for all URLs
                tasks = [
                    self.scrape_page(url, browser, wait_for_selector) 
                    for url in urls
                ]
                
                # Execute all tasks in parallel (with semaphore limiting concurrency)
                results = await asyncio.gather(*tasks)
                
                # Calculate statistics
                total_time = (asyncio.get_event_loop().time() - start_time)
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count
                avg_time = sum(
                    r.duration_ms for r in results if r.duration_ms
                ) / len(results) if results else 0
                
                logger.info(
                    f"Batch complete: {success_count} success, {fail_count} failed "
                    f"in {total_time:.1f}s (avg {avg_time:.0f}ms/page)"
                )
                
                return results
                
            finally:
                await browser.close()
    
    async def scrape_with_pagination(
        self,
        start_url: str,
        next_page_selector: str,
        max_pages: int = 10
    ) -> List[ScrapingResult]:
        """
        Scrape paginated content
        
        Args:
            start_url: Starting URL
            next_page_selector: CSS selector for "next page" button/link
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of ScrapingResults
        """
        logger.info(f"Starting paginated scrape from {start_url}")
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                current_url = start_url
                
                for page_num in range(max_pages):
                    # Scrape current page
                    result = await self.scrape_page(current_url, browser)
                    results.append(result)
                    
                    if not result.success:
                        logger.warning(f"Failed to scrape page {page_num + 1}, stopping")
                        break
                    
                    # Try to find next page link
                    try:
                        await page.goto(current_url)
                        next_button = await page.query_selector(next_page_selector)
                        
                        if not next_button:
                            logger.info(f"No more pages found after page {page_num + 1}")
                            break
                        
                        # Get next page URL
                        next_url = await next_button.get_attribute('href')
                        
                        if not next_url or next_url == current_url:
                            logger.info(f"Reached last page at page {page_num + 1}")
                            break
                        
                        current_url = next_url
                        
                    except Exception as e:
                        logger.warning(f"Error finding next page: {e}")
                        break
                
            finally:
                await page.close()
                await browser.close()
        
        logger.info(f"Paginated scrape complete: {len(results)} pages")
        return results


# Convenience function for simple batch scraping
async def scrape_urls(
    urls: List[str], 
    max_concurrent: int = 5,
    delay_ms: int = 1000
) -> List[ScrapingResult]:
    """
    Simple function to scrape multiple URLs
    
    Args:
        urls: List of URLs to scrape
        max_concurrent: Maximum concurrent requests
        delay_ms: Delay between requests
        
    Returns:
        List of ScrapingResults
    """
    scraper = SmartScraper(max_concurrent=max_concurrent, delay_ms=delay_ms)
    return await scraper.scrape_batch(urls)
