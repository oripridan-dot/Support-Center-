"""
Brand-Specific Scraper Base Class
Provides framework for brand-dedicated scraping systems with multi-browser support
"""

import asyncio
import logging
import random
from typing import Optional, Dict, Any, List, Set
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, BrowserType
from abc import ABC, abstractmethod

# Fix for playwright_stealth import
try:
    from playwright_stealth import stealth_async
except ImportError:
    async def stealth_async(page): 
        pass

logger = logging.getLogger(__name__)


class BrandScraper(ABC):
    """
    Abstract base class for brand-specific scrapers
    Supports multi-browser rotation (Chrome, Firefox, Safari)
    with anti-detection measures and intelligent fallbacks
    """
    
    def __init__(self, brand_name: str, headless: bool = True):
        self.brand_name = brand_name
        self.headless = headless
        self.playwright = None
        self.browsers: Dict[str, Browser] = {}  # browser_type -> Browser instance
        self.context: Optional[BrowserContext] = None
        self.current_browser_type = "chromium"  # Start with Chrome
        self.browser_rotation = ["chromium", "firefox", "webkit"]  # Rotation order
        self.browser_index = 0
        
    @abstractmethod
    def get_official_domains(self) -> Set[str]:
        """Return set of official domains for this brand"""
        pass
    
    @abstractmethod
    def get_discovery_urls(self) -> Dict[str, str]:
        """Return dict of {section_name: url} for discovery"""
        pass
    
    async def _launch_browser(self, browser_type: str) -> Browser:
        """Launch a specific browser type with anti-detection measures"""
        try:
            logger.info(f"Launching {browser_type} browser...")
            
            # Browser-specific launch options
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu"
                ]
            }
            
            if browser_type == "chromium":
                self.browsers[browser_type] = await self.playwright.chromium.launch(**launch_options)
            elif browser_type == "firefox":
                self.browsers[browser_type] = await self.playwright.firefox.launch(**launch_options)
            elif browser_type == "webkit":
                self.browsers[browser_type] = await self.playwright.webkit.launch(**launch_options)
            else:
                raise ValueError(f"Unknown browser type: {browser_type}")
            
            logger.info(f"✓ {browser_type} launched successfully")
            return self.browsers[browser_type]
            
        except Exception as e:
            logger.error(f"Failed to launch {browser_type}: {e}")
            return None
    
    async def start(self):
        """Initialize playwright and launch browsers"""
        self.playwright = await async_playwright().start()
        
        # Launch chromium by default
        browser = await self._launch_browser("chromium")
        if not browser:
            logger.error("Failed to launch any browser!")
            return
        
        # Create context with stealth measures
        self.context = await browser.new_context(
            user_agent=self._get_user_agent(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        
        self.current_browser_type = "chromium"
    
    async def stop(self):
        """Clean up all browsers and playwright"""
        try:
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass  # Context may already be closed
            for browser in self.browsers.values():
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass  # Browser may already be closed
        finally:
            if self.playwright:
                await self.playwright.stop()
    
    async def _rotate_browser(self):
        """Switch to next browser in rotation for anti-detection"""
        self.browser_index = (self.browser_index + 1) % len(self.browser_rotation)
        next_browser_type = self.browser_rotation[self.browser_index]
        
        if next_browser_type not in self.browsers:
            browser = await self._launch_browser(next_browser_type)
            if not browser:
                logger.warning(f"Failed to launch {next_browser_type}, staying with current")
                return
        
        # Close old context if it exists
        if self.context:
            try:
                await self.context.close()
            except:
                pass
        
        # Create new context with new browser
        browser = self.browsers[next_browser_type]
        try:
            self.context = await browser.new_context(
                user_agent=self._get_user_agent(),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
            )
            self.current_browser_type = next_browser_type
            logger.info(f"Rotated to {next_browser_type} browser")
        except Exception as e:
            logger.error(f"Failed to create context for {next_browser_type}: {e}")
            # Fallback - try to recover with chromium
            if next_browser_type != "chromium" and "chromium" in self.browsers:
                browser = self.browsers["chromium"]
                self.context = await browser.new_context(
                    user_agent=self._get_user_agent(),
                    viewport={"width": 1920, "height": 1080},
                )
                self.current_browser_type = "chromium"
    
    def _get_user_agent(self) -> str:
        """Get random user agent for browser"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0",
        ]
        return random.choice(user_agents)
    
    async def get_page(self) -> Page:
        """Get a new page with stealth measures"""
        if not self.context:
            raise RuntimeError("Scraper not started. Call await scraper.start() first")
        
        page = await self.context.new_page()
        await stealth_async(page)
        return page
    
    async def safe_goto(self, page: Page, url: str, retries: int = 3) -> bool:
        """Safely navigate to URL with retry logic and anti-Cloudflare measures"""
        for attempt in range(retries):
            try:
                # Random delay between requests
                await asyncio.sleep(random.uniform(2, 5))
                
                # Check if page is still valid
                try:
                    await page.url  # Quick check if page context is valid
                except:
                    logger.warning(f"[{self.brand_name}] Page context closed, rotating browser")
                    await self._rotate_browser()
                    page = await self.get_page()
                
                # Navigate with DOM content loaded (faster than networkidle)
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Additional wait for JS execution
                await asyncio.sleep(random.uniform(1, 3))
                
                # Check for Cloudflare challenge
                content = await page.content()
                if any(block in content for block in ["Just a moment", "Verify you are human", "Enable JavaScript"]):
                    logger.warning(f"[{self.brand_name}] Cloudflare block on {url} (attempt {attempt+1}/{retries})")
                    
                    # On Cloudflare block, rotate browser
                    await self._rotate_browser()
                    
                    # Wait longer and retry
                    await asyncio.sleep(random.uniform(20, 30))
                    continue
                
                if response and response.status == 200:
                    logger.debug(f"✓ Loaded {url}")
                    return True
                
                if response and response.status == 404:
                    logger.debug(f"404 Not Found: {url}")
                    return False
                
                logger.warning(f"[{self.brand_name}] Status {response.status if response else 'No response'}: {url}")
                
            except Exception as e:
                error_msg = str(e)
                if "Target page, context or browser has been closed" in error_msg:
                    logger.warning(f"[{self.brand_name}] Browser crashed, rotating browser")
                    await self._rotate_browser()
                    page = await self.get_page()
                    # Retry immediately
                    if attempt < retries - 1:
                        continue
                else:
                    logger.warning(f"[{self.brand_name}] Error on {url}: {error_msg[:100]}")
            
            # Wait before retry
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(5, 15))
        
        return False
    
    async def scrape_url(self, url: str) -> Optional[str]:
        """Scrape a single URL and return HTML content"""
        page = None
        try:
            page = await self.get_page()
            success = await self.safe_goto(page, url)
            if success:
                try:
                    return await page.content()
                except Exception as e:
                    logger.warning(f"Failed to get page content after successful navigation: {e}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Exception in scrape_url for {url}: {e}")
            return None
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass  # Page may already be closed
    
    async def scrape_urls_batch(self, urls: List[str], batch_size: int = 5) -> Dict[str, Optional[str]]:
        """Scrape multiple URLs with batching to avoid overwhelming the site"""
        results = {}
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            logger.info(f"[{self.brand_name}] Scraping batch {i//batch_size + 1}/{(len(urls)-1)//batch_size + 1}")
            
            # Scrape batch in parallel
            tasks = [self.scrape_url(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"[{self.brand_name}] Exception scraping {url}: {result}")
                    results[url] = None
                else:
                    results[url] = result
            
            # Delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(random.uniform(5, 10))
        
        return results
    
    @abstractmethod
    async def discover_urls(self) -> Set[str]:
        """Discover all relevant URLs for this brand"""
        pass
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is from official brand domain"""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            return any(domain.endswith(official) for official in self.get_official_domains())
        except:
            return False
