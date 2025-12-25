import asyncio
from playwright.async_api import async_playwright
import random
import os

async def verify_url(page, url):
    try:
        print(f"Checking {url}...")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        content = await page.content()
        if "Just a moment..." in content or "Verify you are human" in content:
            print(f"  [BLOCKED] Cloudflare challenge detected for {url}")
            return False, "blocked"
            
        if response and response.status == 200:
            print(f"  [OK] Found {url}")
            return True, "ok"
        elif response:
            print(f"  [FAIL] Status {response.status} for {url}")
            return False, f"status_{response.status}"
        else:
            print(f"  [FAIL] No response for {url}")
            return False, "no_response"
    except Exception as e:
        print(f"  [ERROR] {str(e)} for {url}")
        return False, "error"

async def main():
    products = [
        "zed-6", "zed-6fx", "zed-10", "zed-10fx", "zed-12fx", "zed-14", "zed-16fx", "zed-22fx", "zed-428",
        "zed60-10fx", "zed60-14fx", "zedi-8", "zedi-10", "zedi-10fx",
        "xone-92", "xone-96", "xone-43", "xone-43c", "xone-23", "xone-23c", "xone-k2", "xone-px5",
        "qu-16", "qu-24", "qu-32", "qu-pac", "qu-sb"
    ]
    
    base_urls = [
        "https://www.allen-heath.com/hardware/zed-series/",
        "https://www.allen-heath.com/hardware/xone-series/",
        "https://www.allen-heath.com/hardware/qu/",
        "https://www.allen-heath.com/hardware/"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Try to apply stealth if possible
        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
        except:
            try:
                from playwright_stealth import stealth
                # stealth(page) # stealth is for sync, but sometimes works in async if not using async features
            except:
                pass

        found_urls = []
        
        print("Visiting home page to establish session...")
        try:
            await page.goto("https://www.allen-heath.com/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
        except:
            print("Home page load timed out, continuing anyway...")

        for prod in products:
            verified = False
            for base in base_urls:
                url = f"{base}{prod}/"
                success, reason = await verify_url(page, url)
                if success:
                    found_urls.append(url)
                    verified = True
                    break
                if reason == "blocked":
                    print("Stopping due to block.")
                    await page.screenshot(path="/workspaces/Support-Center-/backend/ah_blocked.png")
                    await browser.close()
                    return
                
                await asyncio.sleep(random.uniform(3, 7))
            
            if verified:
                print(f"Verified {prod}")
            else:
                print(f"Could not verify {prod}")
            
            await asyncio.sleep(random.uniform(10, 20))

        print("\nSummary of found URLs:")
        for url in found_urls:
            print(url)

        os.makedirs("/workspaces/Support-Center-/backend/data", exist_ok=True)
        with open("/workspaces/Support-Center-/backend/data/ah_guessed_links.txt", "w") as f:
            for url in found_urls:
                f.write(url + "\n")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
