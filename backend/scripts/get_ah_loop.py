
import asyncio
from playwright.async_api import async_playwright

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print("Visiting hardware page...")
        try:
            await page.goto("https://www.allen-heath.com/hardware/", wait_until='domcontentloaded', timeout=60000)
            
            # Wait for challenge to resolve
            for i in range(60):
                content = await page.content()
                if "Just a moment..." not in content and "challenge-platform" not in content:
                    print(f"Challenge resolved after {i} seconds!")
                    break
                if i % 10 == 0:
                    print(f"Still waiting... ({i}s)")
                await asyncio.sleep(1)
            
            await asyncio.sleep(5) # Extra wait for content to load
            
            links = await page.query_selector_all("a")
            urls = set()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith('http'):
                        href = "https://www.allen-heath.com" + href
                    if ('/products/' in href or '/hardware/' in href) and not href.endswith('/products/') and not href.endswith('/hardware/'):
                        urls.add(href.split('#')[0].split('?')[0].rstrip('/'))
            
            print(f"Found {len(urls)} links")
            for u in sorted(list(urls)):
                print(u)
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_ah_links())
