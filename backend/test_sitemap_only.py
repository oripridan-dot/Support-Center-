#!/usr/bin/env python3
"""
Quick test of sitemap parsing only
"""

import asyncio
import sys
sys.path.insert(0, '/workspaces/Support-Center-/backend')

from playwright.async_api import async_playwright
from app.config.brand_configs import get_brand_config
import xml.etree.ElementTree as ET


async def test_sitemap():
    config = get_brand_config("Universal Audio")
    
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        url = "https://www.uaudio.com/sitemap.xml"
        print(f"Fetching: {url}")
        
        response = await asyncio.wait_for(
            page.goto(url, wait_until='load'),
            timeout=10
        )
        
        if response and response.ok:
            content = await page.content()
            print(f"✓ Got {len(content)} bytes")
            
            root = ET.fromstring(content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            nested_sitemaps = root.findall('.//sm:sitemap/sm:loc', ns) + root.findall('.//sitemap/loc')
            print(f"✓ Found {len(nested_sitemaps)} nested sitemaps")
            
            for nested_loc in nested_sitemaps[:1]:  # Just first one
                nested_url = nested_loc.text
                print(f"\nFetching nested: {nested_url[:70]}...")
                
                nested_response = await asyncio.wait_for(
                    page.goto(nested_url, wait_until='load'),
                    timeout=10
                )
                
                if nested_response and nested_response.ok:
                    nested_content = await page.content()
                    print(f"✓ Got {len(nested_content)} bytes")
                    
                    nested_root = ET.fromstring(nested_content)
                    urls = nested_root.findall('.//sm:loc', ns) + nested_root.findall('.//loc')
                    print(f"✓ Found {len(urls)} URLs total")
                    
                    # Check for products
                    product_urls = [u.text for u in urls if u.text and 'product' in u.text.lower()]
                    print(f"✓ Found {len(product_urls)} product URLs")
                    if product_urls:
                        print(f"First 3: {product_urls[:3]}")
    
    finally:
        await browser.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(test_sitemap())
