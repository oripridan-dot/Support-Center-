
import asyncio
from playwright.async_api import async_playwright
import re

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        urls = set()
        
        # Try sitemap first
        sitemap_urls = [
            "https://www.allen-heath.com/sitemap-pt-product-p1.xml",
            "https://www.allen-heath.com/sitemap-pt-product-p2.xml"
        ]
        
        for sitemap_url in sitemap_urls:
            print(f"Visiting sitemap: {sitemap_url}")
            try:
                await page.goto(sitemap_url, wait_until='networkidle', timeout=60000)
            except:
                try:
                    await page.goto(sitemap_url, wait_until='domcontentloaded', timeout=60000)
                except Exception as e:
                    print(f"Failed to load sitemap {sitemap_url}: {e}")
                    continue
            
            await asyncio.sleep(5)
            content = await page.content()
            if "<loc>" in content:
                locs = re.findall(r'<loc>(.*?)</loc>', content)
                print(f"Found {len(locs)} links in {sitemap_url}")
                for l in locs:
                    if '/products/' in l or '/hardware/' in l:
                        urls.add(l)
            else:
                print(f"Sitemap {sitemap_url} content not found or blocked")

        # Also try the hardware page
        print("Visiting hardware page...")
        try:
            await page.goto("https://www.allen-heath.com/hardware/", wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith('http'):
                        href = "https://www.allen-heath.com" + href
                    if ('/products/' in href or '/hardware/' in href) and not href.endswith('/products/') and not href.endswith('/hardware/'):
                        urls.add(href.split('#')[0].split('?')[0].rstrip('/'))
        except Exception as e:
            print(f"Failed to load hardware page: {e}")

        await browser.close()
        
        # Filter and clean URLs
        final_urls = sorted(list(urls))
        with open("ah_urls.txt", "w") as f:
            for url in final_urls:
                f.write(url + "\n")
        print(f"Saved {len(final_urls)} URLs to ah_urls.txt")

if __name__ == "__main__":
    asyncio.run(get_ah_links())
