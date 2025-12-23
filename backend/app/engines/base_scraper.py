import asyncio
import random
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Fix for playwright_stealth import
try:
    from playwright_stealth import stealth_async
except ImportError:
    async def stealth_async(page): pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper:
    def __init__(self, headless: bool = True, user_agent: Optional[str] = None):
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

    async def start(self):
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        except Exception as e:
            logger.warning(f"Failed to launch chromium: {e}. Trying firefox...")
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        
        self.context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080}
        )

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_page(self) -> Page:
        page = await self.context.new_page()
        await stealth_async(page)
        return page

    async def establish_session(self, base_url: str):
        logger.info(f"Establishing session by visiting {base_url}")
        page = await self.get_page()
        try:
            await page.goto(base_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(3, 7))
        except Exception as e:
            logger.warning(f"Failed to establish session: {e}")
        finally:
            await page.close()

    async def safe_goto(self, page: Page, url: str, retries: int = 3) -> bool:
        for i in range(retries):
            try:
                await asyncio.sleep(random.uniform(2, 5))
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for potential redirects or JS challenges
                await asyncio.sleep(2)
                
                content = await page.content()
                if "Just a moment..." in content or "Verify you are human" in content:
                    logger.warning(f"Cloudflare block detected on {url} (Attempt {i+1}/{retries})")
                    await asyncio.sleep(random.uniform(15, 30))
                    continue
                
                if response and response.status == 200:
                    return True
                
                if response and response.status == 404:
                    logger.info(f"URL not found (404): {url}")
                    return False
                
                logger.warning(f"Failed to load {url} with status {response.status if response else 'No Response'}")
            except Exception as e:
                logger.error(f"Error loading {url}: {e}")
            
            await asyncio.sleep(random.uniform(5, 10))
        
        return False

    async def scrape_url(self, url: str) -> Optional[str]:
        page = await self.get_page()
        success = await self.safe_goto(page, url)
        content = None
        if success:
            content = await page.content()
        await page.close()
        return content
