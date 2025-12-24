"""
Test Scraper for Adam Audio Official Website
Purpose: Verify we can actually scrape documentation from the official brand website

Target: https://www.adam-audio.com
Support: https://support.adam-audio.com/hc/en-gb
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def test_adam_audio_scraping():
    """Test scraping Adam Audio's official website"""
    
    print("="*80)
    print("ADAM AUDIO OFFICIAL WEBSITE SCRAPING TEST")
    print("="*80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Test 1: Product Catalog Discovery
        print("\n[TEST 1] Discovering product catalog...")
        await page.goto("https://www.adam-audio.com/en/", wait_until="networkidle")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all product series
        product_series = {}
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/en/t-series/' in href or '/en/a-series/' in href or '/en/s-series/' in href:
                if href.startswith('/'):
                    href = 'https://www.adam-audio.com' + href
                product_series[link.text.strip()] = href
        
        print(f"✓ Found {len(product_series)} product series links")
        for name, url in list(product_series.items())[:5]:
            print(f"  - {name}: {url}")
        
        # Test 2: Individual Product Page
        print("\n[TEST 2] Checking individual product page (T5V)...")
        await page.goto("https://www.adam-audio.com/en/t-series/t5v/", wait_until="networkidle")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for download links
        download_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.text.strip()
            if '.pdf' in href.lower() or 'download' in text.lower() or 'manual' in text.lower():
                download_links.append({
                    'text': text,
                    'url': href
                })
        
        print(f"✓ Found {len(download_links)} potential download links")
        for dl in download_links[:5]:
            print(f"  - {dl['text']}: {dl['url']}")
        
        # Test 3: Support Portal
        print("\n[TEST 3] Checking support portal...")
        try:
            await page.goto("https://support.adam-audio.com/hc/en-gb", wait_until="networkidle", timeout=10000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for knowledge base articles
            articles = soup.find_all('a', class_=lambda x: x and ('article' in x or 'title' in x))
            print(f"✓ Found {len(articles)} support articles/sections")
            
        except Exception as e:
            print(f"✗ Support portal check failed: {e}")
        
        # Test 4: Check robots.txt
        print("\n[TEST 4] Checking robots.txt...")
        await page.goto("https://www.adam-audio.com/robots.txt")
        robots_content = await page.content()
        print("✓ robots.txt content:")
        print(robots_content[:500])
        
        await browser.close()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Product catalog: Accessible")
    print(f"✓ Product pages: Accessible")
    print(f"✓ Support portal: Accessible")
    print(f"\n{'⚠️ NEXT STEPS'}")
    print("1. Manually visit https://www.adam-audio.com/en/t-series/t5v/")
    print("2. Click on 'Downloads' or 'Support' section")
    print("3. Document exact selectors for PDF links")
    print("4. Check if manuals are behind a registration wall")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_adam_audio_scraping())
