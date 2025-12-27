#!/usr/bin/env python3
"""
Quick test: Scrape and ingest ONE brand to verify the pipeline works.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.brand_discovery import brand_discovery_service

async def test_boss():
    print("=" * 80)
    print("TESTING: Boss Brand Scraping & Ingestion")
    print("=" * 80)
    
    brand_name = "Boss"
    
    # Step 1: Discover
    print(f"\n🔍 Step 1: Discovering {brand_name}...")
    try:
        discovery_result = await brand_discovery_service.discover_brand(brand_name)
        print(f"✅ Discovery complete:")
        print(f"   - Products found: {len(discovery_result.get('products', []))}")
        print(f"   - Docs found: {len(discovery_result.get('documentation_links', []))}")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return
    
    # Step 2: Scrape (if strategy exists)
    strategy_path = Path(f"data/strategies/{brand_name.lower().replace(' ', '_')}_strategy.json")
    if strategy_path.exists():
        print(f"\n📄 Step 2: Strategy exists at {strategy_path}")
        print("   → To scrape, you'll need to run the scraper manually")
    else:
        print(f"\n⚠️  No strategy found at {strategy_path}")
        print("   → Create strategy first before scraping")

if __name__ == "__main__":
    asyncio.run(test_boss())
