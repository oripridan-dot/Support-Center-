
import asyncio
from playwright.async_api import async_playwright
import re

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a more realistic context
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        urls = set()
        
        # Try to visit the main hardware page and wait for it to load
        print("Visiting hardware page...")
        try:
            # Go to the main page first to potentially get cookies
            await page.goto("https://www.allen-heath.com/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            await page.goto("https://www.allen-heath.com/hardware/", wait_until='networkidle', timeout=90000)
            # Wait extra time for Cloudflare
            await asyncio.sleep(10)
            
            # Check if we are still on the challenge page
            content = await page.content()
            if "Just a moment..." in content or "challenge-platform" in content:
                print("Still on challenge page, waiting longer...")
                await asyncio.sleep(20)
                content = await page.content()

            # Extract links
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith('http'):
                        href = "https://www.allen-heath.com" + href
                    
                    # Filter for product-like URLs
                    # Allen & Heath URLs often look like /hardware/dlive/ or /products/dlive-s7000/
                    if ('/products/' in href or '/hardware/' in href) and not href.endswith('/products/') and not href.endswith('/hardware/'):
                        # Clean up
                        clean_url = href.split('#')[0].split('?')[0].rstrip('/')
                        urls.add(clean_url)
            
            print(f"Found {len(urls)} potential links on hardware page")
            
        except Exception as e:
            print(f"Error visiting hardware page: {e}")

        # Try sitemap again with the cookies we might have now
        sitemap_url = "https://www.allen-heath.com/sitemap-pt-product-p1.xml"
        print(f"Visiting sitemap: {sitemap_url}")
        try:
            await page.goto(sitemap_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            content = await page.content()
            if "<loc>" in content:
                locs = re.findall(r'<loc>(.*?)</loc>', content)
                print(f"Found {len(locs)} links in sitemap")
                for l in locs:
                    if '/products/' in l or '/hardware/' in l:
                        urls.add(l.rstrip('/'))
            else:
                print("Sitemap still blocked or empty")
        except Exception as e:
            print(f"Error visiting sitemap: {e}")

        await browser.close()
        
        # Filter for hardware products (exclude software, apps, etc. if possible)
        # But for now, let's just get everything and we can filter later
        final_urls = sorted(list(urls))
        
        # Filter out some obvious non-product pages
        filtered_urls = [u for u in final_urls if not any(x in u.lower() for x in ['/category/', '/tag/', '/blog/', '/news/', '/support/', '/where-to-buy/'])]
        
        with open("ah_urls.txt", "w") as f:
            for url in filtered_urls:
                f.write(url + "\n")
        print(f"Saved {len(filtered_urls)} URLs to ah_urls.txt")

if __name__ == "__main__":
    asyncio.run(get_ah_links())
