
import asyncio
from playwright.async_api import async_playwright

async def analyze():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print("Navigating to RCF...")
        try:
            await page.goto('https://www.rcf.it/en/products', wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(10)
            
            # Check for cookie consent
            cookies_btn = await page.query_selector('button:has-text("Accept"), button:has-text("Allow"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll')
            if cookies_btn:
                print("Clicking cookies button...")
                await cookies_btn.click()
                await asyncio.sleep(5)
            
            content = await page.content()
            print(f"Content length: {len(content)}")
            
            # Wait for the cookie dialog to disappear or just look for the main nav
            await asyncio.sleep(5)
            
            # Try to find the main navigation or product categories
            # RCF categories are often in a div with class 'product-categories' or similar
            categories = await page.query_selector_all('.product-category, .category-item, a[href*="/products/"]')
            print(f"Found {len(categories)} potential category links")
            
            for cat in categories:
                href = await cat.get_attribute('href')
                text = await cat.inner_text()
                if href:
                    print(f"Category: {href} | Text: {text.strip()}")
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze())
