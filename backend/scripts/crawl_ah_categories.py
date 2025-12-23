
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Deep-Crawl")

categories = [
    "https://www.allen-heath.com/hardware/ahm",
    "https://www.allen-heath.com/hardware/audio-networking",
    "https://www.allen-heath.com/hardware/cc-7-cc-10",
    "https://www.allen-heath.com/hardware/controllers",
    "https://www.allen-heath.com/hardware/cq",
    "https://www.allen-heath.com/hardware/dlive-series",
    "https://www.allen-heath.com/hardware/everything-i-o",
    "https://www.allen-heath.com/hardware/gr-series",
    "https://www.allen-heath.com/hardware/ip-series",
    "https://www.allen-heath.com/hardware/me-series",
    "https://www.allen-heath.com/hardware/mixwizard4-series",
    "https://www.allen-heath.com/hardware/qu",
    "https://www.allen-heath.com/hardware/sq",
    "https://www.allen-heath.com/hardware/xb-series",
    "https://www.allen-heath.com/hardware/xone-series",
    "https://www.allen-heath.com/hardware/zed-series"
]

async def crawl_ah():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        all_product_links = set()
        
        for cat in categories:
            logger.info(f"Crawling category: {cat}")
            try:
                # Use a longer timeout and wait for domcontentloaded
                await page.goto(cat, wait_until='domcontentloaded', timeout=90000)
                
                # Wait for a bit to let JS run
                await asyncio.sleep(5)
                
                # Scroll a bit
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)
                
                links = await page.query_selector_all("a")
                logger.info(f"Found {len(links)} links on {cat}")
                
                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        if not href.startswith('http'):
                            href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                        href = href.split('#')[0].split('?')[0].rstrip('/')
                        
                        # Filter for product links
                        if "/hardware/" in href and len(href.split('/')) > 5:
                            if not any(x in href for x in ['/resources/', '/processing-expansion/', '/all-models/', '/where-to-buy/', '/case-studies/']):
                                all_product_links.add(href)
                
                logger.info(f"Found {len(all_product_links)} total unique links so far")
            except Exception as e:
                logger.error(f"Error crawling {cat}: {e}")
                await page.screenshot(path=f"ah_crawl_error_{cat.split('/')[-1]}.png")
        
        with open("ah_discovered_links_v3.txt", "w") as f:
            for url in sorted(list(all_product_links)):
                f.write(url + "\n")
        
        logger.info(f"Finished. Total unique product links: {len(all_product_links)}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_ah())
