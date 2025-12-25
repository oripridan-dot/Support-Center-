
import sys
import os
import json
import asyncio
import aiohttp
import logging
from pathlib import Path
import hashlib

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.vector_db import get_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BRAND_DOCS_DIR = Path("data/brand_docs")

async def download_file(session, url, dest_path):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                with open(dest_path, 'wb') as f:
                    f.write(content)
                return True
            else:
                logger.error(f"Failed to download {url}: Status {response.status}")
                return False
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

async def process_brand_pdfs(brand_name):
    logger.info(f"Processing PDFs for brand: {brand_name}")
    
    collection = get_collection()
    
    # Query for documents of this brand that have PDFs
    # Note: ChromaDB filtering on JSON string fields is hard.
    # We'll fetch all docs for the brand and parse the 'pdfs' metadata field.
    
    results = collection.get(
        where={"brand": brand_name},
        include=["metadatas"]
    )
    
    if not results['ids']:
        logger.warning(f"No documents found for brand {brand_name}")
        return

    brand_dir = BRAND_DOCS_DIR / brand_name.lower().replace(' ', '_')
    brand_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = brand_dir / "download_manifest.json"
    manifest = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except:
            pass
            
    existing_urls = {m['url'] for m in manifest}
    new_pdfs = []
    
    for meta in results['metadatas']:
        pdfs_json = meta.get('pdfs', '[]')
        try:
            pdf_links = json.loads(pdfs_json)
            product_name = meta.get('product', 'Unknown')
            
            for link in pdf_links:
                url = link.get('url')
                title = link.get('title', 'manual')
                
                if url and url not in existing_urls:
                    # Generate filename
                    # Use hash of URL to ensure uniqueness and avoid filesystem issues
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    safe_title = "".join([c if c.isalnum() else "_" for c in title])[:30]
                    filename = f"{product_name.replace(' ', '_')}_{safe_title}_{url_hash}.pdf"
                    filepath = brand_dir / filename
                    
                    new_pdfs.append({
                        "url": url,
                        "filepath": str(filepath),
                        "product_name": product_name,
                        "doc_type": title,
                        "brand": brand_name
                    })
                    existing_urls.add(url)
        except json.JSONDecodeError:
            continue

    logger.info(f"Found {len(new_pdfs)} new PDFs to download")
    
    async with aiohttp.ClientSession() as session:
        for pdf in new_pdfs:
            logger.info(f"Downloading: {pdf['url']}")
            success = await download_file(session, pdf['url'], pdf['filepath'])
            if success:
                manifest.append(pdf)
            else:
                logger.warning(f"Skipping manifest entry for failed download: {pdf['url']}")
    
    # Save updated manifest
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Updated manifest with {len(manifest)} entries")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(process_brand_pdfs(sys.argv[1]))
    else:
        logger.error("Please provide a brand name")
