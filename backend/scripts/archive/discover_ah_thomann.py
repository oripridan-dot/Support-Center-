import requests
import json
import time
import re

def discover_ah_thomann():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    products = []
    # Thomann search results pagination
    for page in range(1, 5):
        url = f"https://www.thomann.nl/search_dir.html?sw=allen%20heath&pg={page}"
        print(f"Scraping {url}...")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to scrape page {page}: {response.status_code}")
            break
            
        # Find the JSON data in the script tags
        # Look for dataLayer.push({"ecommerce": ... "items": [...]})
        matches = re.findall(r'dataLayer\.push\({"ecommerce":.*?"items":(\[.*?\])\}\}\)', response.text, re.DOTALL)
        
        if matches:
            for match in matches:
                try:
                    items = json.loads(match)
                    for item in items:
                        if item.get("item_brand") == "Allen & Heath":
                            products.append({
                                "name": item.get("item_name"),
                                "id": item.get("item_id"),
                                "category": item.get("item_category"),
                                "price": item.get("price"),
                                "brand": "Allen Heath"
                            })
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
        else:
            print(f"No JSON data found on page {page}")
        
        time.sleep(2)
        
    print(f"Found {len(products)} products on Thomann.")
    # Remove duplicates by ID
    unique_products = {p['id']: p for p in products}.values()
    print(f"Unique products: {len(unique_products)}")
    
    with open("ah_thomann_products.json", "w") as f:
        json.dump(list(unique_products), f, indent=2)

if __name__ == "__main__":
    discover_ah_thomann()
