import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RCF-Discovery")

async def discover_rcf_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        base_url = "https://www.rcf.it/en"
        start_urls = [
            "https://www.rcf.it/en/products",
            "https://www.rcf.it/en/pro-sound",
            "https://www.rcf.it/en/live-sound",
            "https://www.rcf.it/en/installed-sound",
            "https://www.rcf.it/en/recording",
            "https://www.rcf.it/en/transducers",
            "https://www.rcf.it/en/mixing-consoles",
            "https://www.rcf.it/en/power-amplifiers",
            "https://www.rcf.it/en/headphones"
        ]
        
        product_links = set()
        
        for url in start_urls:
            try:
                logger.info(f"Visiting {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)
                
                title = await page.title()
                logger.info(f"Page Title: {title}")
                
                # Check for cookie banner
                try:
                    await page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=2000)
                    logger.info("Clicked cookie banner")
                except:
                    pass

                # Scroll to bottom to trigger lazy loading
                for _ in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                
                # Debug: Take screenshot
                await page.screenshot(path=f"/workspaces/Support-Center-/backend/data/rcf_debug_{url.split('/')[-1]}.png")
                
                links = await page.query_selector_all("a")
                logger.info(f"Found {len(links)} total links on {url}")
                
                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        # logger.info(f"Href: {href}")
                        if '/product-detail/' in href or '/products/detail/' in href:
                            if not href.startswith('http'):
                                href = "https://www.rcf.it" + href
                            product_links.add(href)
                        elif url == "https://www.rcf.it/en/products" and "/en/" in href and href not in start_urls:
                             # Add discovered categories to the list to visit
                             full_url = "https://www.rcf.it" + href if not href.startswith('http') else href
                             if full_url not in start_urls and "rcf.it" in full_url:
                                 logger.info(f"Discovered potential category: {full_url}")
                                 # We can't append to the list we are iterating over safely in all languages, 
                                 # but in Python it's risky. Better to use a queue or just print for now.
                                 pass
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
        
        logger.info(f"Found {len(product_links)} unique product links")
        
        output_file = "/workspaces/Support-Center-/backend/data/rcf_links.txt"
        with open(output_file, "w") as f:
            for link in sorted(list(product_links)):
                f.write(link + "\n")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_rcf_links())
