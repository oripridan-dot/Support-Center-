#!/usr/bin/env python3
"""
Test the new multi-strategy discovery engine
"""

import asyncio
import sys
sys.path.insert(0, '/workspaces/Support-Center-/backend')

from app.workers.explorer import ExplorerWorker
from app.core.database import get_session
from app.models.sql_models import Brand
from sqlmodel import select


async def main():
    """Test Universal Audio discovery"""
    print("=" * 60)
    print("TESTING ENHANCED DISCOVERY ENGINE")
    print("=" * 60)
    print()
    
    brand_id = 1  # Universal Audio
    
    # Get brand
    session = next(get_session())
    brand = session.exec(select(Brand).where(Brand.id == brand_id)).first()
    
    if not brand:
        print(f"❌ Brand {brand_id} not found")
        return
    
    print(f"🚀 Starting exploration for {brand.name} ({brand.website_url})")
    print()
    
    # Create explorer
    explorer = ExplorerWorker()
    
    try:
        await explorer.initialize()
        print("✓ Browser initialized")
        
        strategy = await explorer.explore_brand(brand_id)
        
        print()
        print("=" * 60)
        print("DISCOVERY RESULTS")
        print("=" * 60)
        print(f"Brand: {strategy.brand_name}")
        print(f"Base URL: {strategy.base_url}")
        print(f"Documents Found: {len(strategy.documentation_urls)}")
        print(f"Requires JavaScript: {strategy.requires_javascript}")
        print()
        
        if strategy.documentation_urls:
            print("📄 Discovered Documentation:")
            for idx, doc in enumerate(strategy.documentation_urls[:15], 1):
                print(f"  {idx}. [{doc.type}] {doc.url[:80]}")
                if doc.title:
                    print(f"      Title: {doc.title[:60]}")
            
            if len(strategy.documentation_urls) > 15:
                print(f"  ... and {len(strategy.documentation_urls) - 15} more")
        else:
            print("⚠️  No documentation found!")
        
        print()
        print("✅ Exploration complete!")
        
    except Exception as e:
        print(f"❌ Error during exploration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🧹 Cleaning up...")
        await explorer.shutdown()
        print("✓ Browser closed")


if __name__ == "__main__":
    asyncio.run(main())

