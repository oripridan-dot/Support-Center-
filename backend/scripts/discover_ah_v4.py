
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Discovery-V4")

async def discover():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        logger.info("Visiting products page...")
        try:
            await page.goto("https://www.allen-heath.com/products/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10) # Wait for JS to render everything
            
            # Scroll to bottom to trigger any lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(5)
            
            links = await page.query_selector_all("a")
            logger.info(f"Found {len(links)} links")
            
            product_links = set()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith('http'):
                        href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                    href = href.split('#')[0].split('?')[0].rstrip('/')
                    
                    if "/hardware/" in href and len(href.split('/')) > 5:
                        if not any(x in href for x in ['/resources/', '/processing-expansion/', '/all-models/', '/where-to-buy/']):
                            product_links.add(href)
            
            logger.info(f"Found {len(product_links)} unique product links")
            with open("ah_links_v4.txt", "w") as f:
                for l in sorted(list(product_links)):
                    f.write(l + "\n")
                    
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path="ah_v4_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(discover())
