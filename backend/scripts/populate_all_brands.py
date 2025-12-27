#!/usr/bin/env python3
"""
Populate All 80 Halilit Brands into Database

Reads HALILIT_BRANDS_LIST.md and creates/updates all brand records.
Preserves existing brands and only adds missing ones.
"""

import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand
from sqlmodel import Session, select


# Brand data from HALILIT_BRANDS_LIST.md
BRANDS = [
    {"id": 31, "name": "EAW Eastern Acoustic Works", "website": None},
    {"id": 11, "name": "Adam Audio", "website": "https://adam-audio.com"},
    {"id": 60, "name": "Adams", "website": None},
    {"id": 5, "name": "Akai Professional", "website": "https://www.akaipro.com"},
    {"id": 28, "name": "Allen & Heath", "website": "https://www.allen-heath.com"},
    {"id": 79, "name": "Amphion", "website": None},
    {"id": 55, "name": "Antigua", "website": None},
    {"id": 18, "name": "Ashdown Engineering", "website": "https://ashdownmusic.com"},
    {"id": 26, "name": "ASM", "website": None},
    {"id": 78, "name": "Austrian Audio", "website": None},
    {"id": 32, "name": "Avid", "website": "https://www.avid.com"},
    {"id": 61, "name": "Bespeco", "website": None},
    {"id": 38, "name": "Bohemian Ukuleles Guitars Basses", "website": None},
    {"id": 2, "name": "Boss", "website": "https://www.boss.info"},
    {"id": 43, "name": "Breedlove Guitars", "website": None},
    {"id": 37, "name": "Cordoba Guitars", "website": None},
    {"id": 85, "name": "Dixon", "website": None},
    {"id": 75, "name": "Drumdots", "website": None},
    {"id": 65, "name": "Dynaudio", "website": None},
    {"id": 83, "name": "Eden", "website": None},
    {"id": 87, "name": "Encore", "website": None},
    {"id": 14, "name": "ESP", "website": "https://www.espguitars.com"},
    {"id": 52, "name": "Eve Audio", "website": "https://www.eve-audio.com"},
    {"id": 71, "name": "Expressive E", "website": None},
    {"id": 39, "name": "Foxgear Guitar Effects and Pedals", "website": None},
    {"id": 63, "name": "Fusion", "website": None},
    {"id": 67, "name": "Fzone", "website": None},
    {"id": 66, "name": "Gon Bops Percussion", "website": None},
    {"id": 42, "name": "Guild", "website": None},
    {"id": 23, "name": "Headliner LA Equipment Stands", "website": None},
    {"id": 22, "name": "Headrush FX", "website": None},
    {"id": 17, "name": "Heritage Audio", "website": None},
    {"id": 16, "name": "Hiwatt", "website": None},
    {"id": 74, "name": "Innovative Percussion", "website": None},
    {"id": 30, "name": "Jasmine Guitars", "website": None},
    {"id": 33, "name": "Keith McMillen Instruments KMI", "website": None},
    {"id": 13, "name": "KRK Systems", "website": "https://www.krkmusic.com"},
    {"id": 77, "name": "Lag Guitars", "website": None},
    {"id": 35, "name": "Lynx", "website": None},
    {"id": 44, "name": "M-Audio", "website": "https://www.m-audio.com"},
    {"id": 21, "name": "Mackie", "website": "https://mackie.com"},
    {"id": 40, "name": "Maestro Guitar Pedals and Effects", "website": None},
    {"id": 80, "name": "Magma", "website": None},
    {"id": 86, "name": "Marimba One", "website": None},
    {"id": 24, "name": "Maton Guitars", "website": None},
    {"id": 36, "name": "Maybach", "website": None},
    {"id": 46, "name": "Medeli", "website": None},
    {"id": 76, "name": "MJC Ironworks", "website": None},
    {"id": 50, "name": "Montarbo", "website": "https://www.montarbo.com"},
    {"id": 12, "name": "Nord", "website": "https://www.nordkeyboards.com"},
    {"id": 25, "name": "Oberheim", "website": None},
    {"id": 56, "name": "On-Stage", "website": None},
    {"id": 49, "name": "Oscar Schmidt Acoustic Guitars", "website": None},
    {"id": 47, "name": "Paiste Cymbals", "website": None},
    {"id": 8, "name": "Pearl", "website": "https://pearldrum.com"},
    {"id": 70, "name": "Perri's Leathers", "website": None},
    {"id": 69, "name": "PreSonus", "website": "https://www.presonus.com"},
    {"id": 59, "name": "Rapier 33 Electric Guitars", "website": None},
    {"id": 84, "name": "Regal Tip", "website": None},
    {"id": 41, "name": "Remo", "website": None},
    {"id": 64, "name": "Rhythm Tech", "website": None},
    {"id": 81, "name": "Rogers", "website": None},
    {"id": 1, "name": "Roland", "website": "https://www.roland.com"},
    {"id": 58, "name": "Santos Martinez", "website": None},
    {"id": 72, "name": "Show", "website": None},
    {"id": 82, "name": "Solar Guitars", "website": None},
    {"id": 20, "name": "Sonarworks", "website": "https://www.sonarworks.com"},
    {"id": 34, "name": "Steinberg", "website": "https://www.steinberg.net"},
    {"id": 68, "name": "Studio Logic", "website": None},
    {"id": 53, "name": "Tombo", "website": None},
    {"id": 62, "name": "Topp Pro", "website": None},
    {"id": 57, "name": "Turkish", "website": None},
    {"id": 19, "name": "Ultimate Support", "website": None},
    {"id": 7, "name": "Universal Audio", "website": "https://www.uaudio.com"},
    {"id": 27, "name": "V-Moda", "website": None},
    {"id": 73, "name": "Vintage", "website": None},
    {"id": 29, "name": "Warm Audio", "website": "https://www.warmaudio.com"},
    {"id": 48, "name": "Washburn", "website": None},
    {"id": 45, "name": "Xotic", "website": None},
    {"id": 51, "name": "Xvive", "website": None},
]


def normalize_brand_name(name: str) -> str:
    """Normalize brand name for comparison"""
    return name.lower().strip().replace("  ", " ")


def populate_brands():
    """Add all missing brands to the database"""
    
    print("=" * 80)
    print("🏭 POPULATING HALILIT BRANDS DATABASE")
    print("=" * 80)
    print(f"Total brands to process: {len(BRANDS)}")
    print()
    
    session = Session(engine)
    
    try:
        # Get existing brands
        existing_brands = session.exec(select(Brand)).all()
        existing_names = {normalize_brand_name(b.name): b for b in existing_brands}
        existing_ids = {b.id: b for b in existing_brands}
        
        print(f"📊 Currently in database: {len(existing_brands)} brands")
        print()
        
        added_count = 0
        updated_count = 0
        skipped_count = 0
        
        for brand_data in BRANDS:
            brand_id = brand_data["id"]
            brand_name = brand_data["name"]
            website = brand_data.get("website")
            
            norm_name = normalize_brand_name(brand_name)
            
            # Check if brand exists by ID
            if brand_id in existing_ids:
                existing_brand = existing_ids[brand_id]
                
                # Update if name or website changed
                needs_update = False
                if normalize_brand_name(existing_brand.name) != norm_name:
                    print(f"📝 Updating brand {brand_id}: {existing_brand.name} → {brand_name}")
                    existing_brand.name = brand_name
                    needs_update = True
                
                if website and existing_brand.website_url != website:
                    print(f"🔗 Updating website for {brand_name}: {website}")
                    existing_brand.website_url = website
                    needs_update = True
                
                if needs_update:
                    session.add(existing_brand)
                    updated_count += 1
                else:
                    skipped_count += 1
                    
            # Check if brand exists by name (different ID)
            elif norm_name in existing_names:
                existing_brand = existing_names[norm_name]
                print(f"⚠️  Brand '{brand_name}' exists with different ID: {existing_brand.id} (wanted {brand_id})")
                print(f"   Keeping existing ID: {existing_brand.id}")
                skipped_count += 1
                
            # Brand doesn't exist - create it
            else:
                print(f"✨ Adding new brand: {brand_id}. {brand_name}")
                new_brand = Brand(
                    id=brand_id,
                    name=brand_name,
                    website_url=website,
                    description=None,
                    logo_url=None,
                    primary_color=None,
                    secondary_color=None
                )
                session.add(new_brand)
                added_count += 1
        
        # Commit all changes
        session.commit()
        
        # Final report
        print()
        print("=" * 80)
        print("✅ BRAND POPULATION COMPLETE")
        print("=" * 80)
        print(f"✨ New brands added:     {added_count}")
        print(f"📝 Existing brands updated: {updated_count}")
        print(f"⏭️  Brands skipped:         {skipped_count}")
        print(f"📊 Total in database:    {len(existing_brands) + added_count}")
        print("=" * 80)
        
        if added_count > 0:
            print()
            print("🎯 Next Steps:")
            print("   1. Restart the backend to ensure all brands are loaded")
            print("   2. Use 'All Brands' mode to start exploring all brands")
            print("   3. Check HALILIT_BRANDS_LIST.md for priority brands to process first")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    populate_brands()
