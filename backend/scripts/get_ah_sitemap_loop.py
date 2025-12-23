
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Sitemap")

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        sitemap_url = "https://www.allen-heath.com/sitemap-pt-product-p1.xml"
        print(f"Visiting sitemap: {sitemap_url}")
        try:
            logger.info(f"Visiting sitemap: {sitemap_url}")
            await page.goto(sitemap_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for challenge to resolve
            for i in range(30):
                content = await page.content()
                if "<loc>" in content:
                    logger.info(f"Sitemap loaded after {i} seconds!")
                    break
                await asyncio.sleep(2)
            
            content = await page.content()
            if "<loc>" in content:
                with open("ah_sitemap_dump.xml", "w") as f:
                    f.write(content)
                locs = re.findall(r'<loc>(.*?)</loc>', content)
                logger.info(f"Found {len(locs)} links in sitemap")
                for l in sorted(list(set(locs))):
                    if "/hardware/" in l:
                        print(l)
            else:
                logger.warning("Sitemap still blocked or empty")
                await page.screenshot(path="ah_sitemap_fail.png")
            
            content = await page.content()
            if "<loc>" in content:
                with open("ah_sitemap_content.xml", "w") as f:
                    f.write(content)
                locs = re.findall(r'<loc>(.*?)</loc>', content)
                print(f"Found {len(locs)} links in sitemap")
                urls = set()
                for l in locs:
                    if '/products/' in l or '/hardware/' in l:
                        urls.add(l.rstrip('/'))
                
                for u in sorted(list(urls)):
                    print(u)
            else:
                print("Sitemap still blocked or empty")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_ah_links())
