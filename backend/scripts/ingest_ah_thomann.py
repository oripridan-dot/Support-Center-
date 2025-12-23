import json
import sqlite3
import re

def ingest_ah_thomann():
    with open("ah_thomann_products.json", "r") as f:
        products = json.load(f)
    
    conn = sqlite3.connect("/workspaces/Support-Center-/backend/support_center.db")
    cursor = conn.cursor()
    
    # Get brand ID for Allen Heath
    cursor.execute("SELECT id FROM brand WHERE name = 'Allen Heath'")
    brand_id = cursor.fetchone()[0]
    
    # Function to determine family
    def get_family(name):
        name = name.upper()
        if "DLIVE" in name: return "dLive Series"
        if "AVANTIS" in name: return "Avantis Series"
        if "SQ" in name: return "SQ Series"
        if "QU" in name: return "Qu Series"
        if "ZED" in name: return "ZED Series"
        if "XONE" in name: return "Xone DJ"
        if "AHM" in name: return "AHM Series"
        if "MIXWIZARD" in name or "WZ4" in name: return "MixWizard Series"
        if "ME-" in name or "ME1" in name or "ME500" in name: return "ME Personal Mixing"
        if "DX" in name or "AB168" in name or "AR2412" in name or "AR84" in name: return "Everything I/O"
        return "Other Products"

    families = {}
    
    for p in products:
        family_name = get_family(p['name'])
        
        if family_name not in families:
            # Check if family exists
            cursor.execute("SELECT id FROM productfamily WHERE name = ? AND brand_id = ?", (family_name, brand_id))
            row = cursor.fetchone()
            if row:
                families[family_name] = row[0]
            else:
                cursor.execute("INSERT INTO productfamily (name, brand_id) VALUES (?, ?)", (family_name, brand_id))
                families[family_name] = cursor.lastrowid
        
        family_id = families[family_name]
        
        # Check if product exists
        cursor.execute("SELECT id FROM product WHERE name = ? AND family_id = ?", (p['name'], family_id))
        if not cursor.fetchone():
            print(f"Adding product: {p['name']} to family {family_name}")
            cursor.execute("INSERT INTO product (name, description, family_id) VALUES (?, ?, ?)", 
                           (p['name'], f"Allen & Heath {p['name']} - {p.get('category', '')}", family_id))
    
    conn.commit()
    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_ah_thomann()
