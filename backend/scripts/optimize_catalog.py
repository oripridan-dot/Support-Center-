"""
Database Optimization & Restructuring Script
1. Deduplicates documents based on content hash.
2. Links unlinked documents to products using fuzzy matching.
3. Updates brand statistics.
4. Cleans up orphaned records.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from sqlmodel import Session, select, func, delete
from fuzzywuzzy import fuzz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand, Product, ProductFamily, Document, IngestLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def optimize_catalog():
    logger.info("=" * 60)
    logger.info("🚀 STARTING CATALOG OPTIMIZATION")
    logger.info("=" * 60)
    
    with Session(engine) as session:
        # 1. Deduplication
        logger.info("\n🧹 Checking for duplicates...")
        duplicates = session.exec(
            select(Document.content_hash, func.count(Document.id))
            .group_by(Document.content_hash)
            .having(func.count(Document.id) > 1)
        ).all()
        
        removed_count = 0
        for content_hash, count in duplicates:
            if not content_hash: continue
            
            # Get all docs with this hash
            docs = session.exec(
                select(Document)
                .where(Document.content_hash == content_hash)
                .order_by(Document.last_updated.desc())
            ).all()
            
            # Keep the most recent one, delete others
            keep_doc = docs[0]
            for doc in docs[1:]:
                session.delete(doc)
                removed_count += 1
        
        session.commit()
        logger.info(f"✅ Removed {removed_count} duplicate documents")

        # 2. Link Unlinked Documents
        logger.info("\n🔗 Linking orphaned documents...")
        unlinked_docs = session.exec(
            select(Document).where(Document.product_id == None)
        ).all()
        
        linked_count = 0
        
        # Pre-fetch all products to avoid N+1 queries
        all_products = session.exec(select(Product)).all()
        products_map = {p.id: p.name.lower() for p in all_products}
        
        for doc in unlinked_docs:
            if not doc.title: continue
            
            best_match_id = None
            best_score = 0
            
            # Simple containment check first (faster)
            doc_title_lower = doc.title.lower()
            
            # Filter products by brand if possible
            brand_products = [
                p for p in all_products 
                if p.family and p.family.brand_id == doc.brand_id
            ]
            
            # Sort by length desc to match specific models first
            brand_products.sort(key=lambda p: len(p.name), reverse=True)
            
            for product in brand_products:
                p_name = product.name.lower()
                if p_name in doc_title_lower:
                    best_match_id = product.id
                    break # Found exact containment
                
                # Fuzzy match if no exact containment
                score = fuzz.token_set_ratio(p_name, doc_title_lower)
                if score > 85 and score > best_score:
                    best_score = score
                    best_match_id = product.id
            
            if best_match_id:
                doc.product_id = best_match_id
                session.add(doc)
                linked_count += 1
        
        session.commit()
        logger.info(f"✅ Linked {linked_count} documents to products")

        # 3. Update Brand Stats (Optional, as API calculates on fly, but good for sanity check)
        logger.info("\n📊 Catalog Statistics:")
        brands = session.exec(select(Brand)).all()
        for brand in brands:
            doc_count = session.exec(
                select(func.count(Document.id)).where(Document.brand_id == brand.id)
            ).one()
            logger.info(f"  - {brand.name}: {doc_count} documents")

    logger.info("\n✨ Optimization Complete!")

if __name__ == "__main__":
    optimize_catalog()
