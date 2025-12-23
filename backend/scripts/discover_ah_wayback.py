import requests
import json
import os
from urllib.parse import urlparse

def discover_ah_links_wayback():
    base_url = "http://web.archive.org/cdx/search/cdx"
    
    # We want unique URLs (collapse=urlkey) that returned 200 OK and are HTML
    params = {
        'url': 'allen-heath.com/hardware/*',
        'output': 'json',
        'fl': 'original',
        'filter': ['statuscode:200', 'mimetype:text/html'],
        'collapse': 'urlkey'
    }
    
    print("Querying Wayback Machine CDX API...")
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # The first item is the header
        if not data or len(data) < 2:
            print("No data found.")
            return

        links = [row[0] for row in data[1:]]
        
        # Filter out irrelevant links (assets, etc if any slipped through)
        product_links = []
        for link in links:
            # Basic filtering to keep likely product pages
            # A&H structure seems to be /hardware/series/product
            parts = urlparse(link).path.strip('/').split('/')
            if len(parts) >= 2: # at least hardware/something
                 product_links.append(link)

        print(f"Found {len(product_links)} unique product links.")
        
        output_file = os.path.join(os.path.dirname(__file__), '../data/ah_wayback_links.txt')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            for link in sorted(product_links):
                f.write(link + '\n')
                
        print(f"Saved links to {output_file}")
        
    except Exception as e:
        print(f"Error querying Wayback Machine: {e}")

if __name__ == "__main__":
    discover_ah_links_wayback()
