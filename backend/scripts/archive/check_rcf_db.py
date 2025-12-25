
import os
import sys

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.vector_db import get_collection

def list_rcf_urls():
    collection = get_collection()
    results = collection.get()
    
    urls = set()
    if results and 'metadatas' in results:
        for meta in results['metadatas']:
            if meta and 'url' in meta:
                url = meta['url']
                if 'rcf.it' in url or 'rcf.com' in url:
                    urls.add(url)
    
    print(f"Found {len(urls)} RCF URLs in Vector DB")
    for url in sorted(list(urls)):
        print(url)

if __name__ == "__main__":
    list_rcf_urls()
