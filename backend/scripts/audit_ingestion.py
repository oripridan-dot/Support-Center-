#!/usr/bin/env python3
"""
Audit and Deduplication Script
Removes duplicate content from ChromaDB and SQL database
Ensures high-quality, unique documentation
"""

import asyncio
import logging
import hashlib
from typing import Dict, Set, List, Tuple
from app.core.database import Session, engine
from app.core.vector_db import get_collection
from app.models.sql_models import Brand, Document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("audit_dedup.log")
    ]
)

logger = logging.getLogger("Audit-Dedup")


class ContentDeduplicator:
    def __init__(self):
        self.duplicate_docs: List[Tuple[int, int]] = []  # (doc_id, duplicate_doc_id)
        self.removed_count = 0
        
    async def audit_all_brands(self):
        """Audit all brands for duplicates"""
        logger.info("=" * 80)
        logger.info("Starting Brand Audit & Deduplication")
        logger.info("=" * 80)
        
        with Session(engine) as session:
            brands = session.exec(select(Brand)).all()
            
            for brand in brands:
                await self.audit_brand(brand)
    
    async def audit_brand(self, brand: Brand):
        """Audit a single brand"""
        logger.info(f"\nAuditing brand: {brand.name} (ID: {brand.id})")
        
        with Session(engine) as session:
            # Get all documents for this brand
            docs = session.exec(
                select(Document).where(Document.brand_id == brand.id)
            ).all()
            
            logger.info(f"  Total documents: {len(docs)}")
            
            if len(docs) == 0:
                logger.info(f"  ✓ No documents to audit")
                return
            
            # Build content hash map
            content_hashes: Dict[str, List[int]] = {}
            
            for doc in docs:
                if not doc.content_hash:
                    logger.warning(f"    Missing content hash for doc {doc.id}: {doc.url}")
                    continue
                
                if doc.content_hash not in content_hashes:
                    content_hashes[doc.content_hash] = []
                content_hashes[doc.content_hash].append(doc.id)
            
            # Find duplicates
            duplicates_found = 0
            for content_hash, doc_ids in content_hashes.items():
                if len(doc_ids) > 1:
                    duplicates_found += len(doc_ids) - 1
                    logger.info(f"  Found {len(doc_ids)} identical documents:")
                    for doc_id in doc_ids:
                        doc = session.get(Document, doc_id)
                        logger.info(f"    - {doc.url}")
                    
                    # Mark for removal (keep first, remove others)
                    for doc_id in doc_ids[1:]:
                        self.duplicate_docs.append((doc_ids[0], doc_id))
            
            logger.info(f"  Duplicates found: {duplicates_found}")
            
            # Report statistics
            unique_count = len(content_hashes)
            logger.info(f"  Unique document content: {unique_count}")
            logger.info(f"  Deduplication ratio: {(1 - unique_count/len(docs))*100:.1f}%")
    
    async def remove_duplicates(self):
        """Remove duplicate documents from database and vector DB"""
        logger.info("\n" + "=" * 80)
        logger.info("Removing Duplicates")
        logger.info("=" * 80)
        
        if not self.duplicate_docs:
            logger.info("No duplicates to remove!")
            return
        
        logger.info(f"Found {len(self.duplicate_docs)} documents to remove")
        
        collection = get_collection()
        
        with Session(engine) as session:
            for keep_id, remove_id in self.duplicate_docs:
                try:
                    doc_to_remove = session.get(Document, remove_id)
                    doc_to_keep = session.get(Document, keep_id)
                    
                    if not doc_to_remove:
                        logger.warning(f"Document {remove_id} not found")
                        continue
                    
                    logger.info(f"Removing duplicate: {remove_id}")
                    logger.info(f"  Keeping: {doc_to_keep.url}")
                    logger.info(f"  Removing: {doc_to_remove.url}")
                    
                    # Remove from ChromaDB by filtering for doc_id in metadata
                    try:
                        results = collection.get(
                            where={"doc_id": remove_id},
                            include=[]
                        )
                        if results['ids']:
                            collection.delete(ids=results['ids'])
                            logger.info(f"    Deleted {len(results['ids'])} vectors from ChromaDB")
                    except Exception as e:
                        logger.warning(f"    Could not delete from ChromaDB: {e}")
                    
                    # Remove from SQL database
                    session.delete(doc_to_remove)
                    session.commit()
                    self.removed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error removing duplicate {remove_id}: {e}")
                    session.rollback()
        
        logger.info(f"\n✅ Successfully removed {self.removed_count} duplicate documents")
    
    async def verify_brand_quality(self, brand_name: str):
        """Detailed quality report for a specific brand"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Quality Report: {brand_name}")
        logger.info(f"{'=' * 80}")
        
        with Session(engine) as session:
            brand = session.exec(
                select(Brand).where(Brand.name == brand_name)
            ).first()
            
            if not brand:
                logger.error(f"Brand '{brand_name}' not found")
                return
            
            docs = session.exec(
                select(Document).where(Document.brand_id == brand.id)
            ).all()
            
            # Statistics
            total_docs = len(docs)
            docs_with_hash = len([d for d in docs if d.content_hash])
            docs_with_product = len([d for d in docs if d.product_id])
            
            logger.info(f"Total Documents: {total_docs}")
            logger.info(f"Documents with content hash: {docs_with_hash} ({docs_with_hash/total_docs*100:.1f}%)")
            logger.info(f"Documents linked to products: {docs_with_product} ({docs_with_product/total_docs*100:.1f}%)")
            
            # Sample URLs
            logger.info(f"\nSample URLs:")
            for doc in docs[:5]:
                logger.info(f"  - {doc.url}")
            
            # Coverage by domain path
            domain_paths = {}
            for doc in docs:
                # Extract main path section
                path = doc.url.split('/')
                if len(path) > 3:
                    main_section = path[3]  # e.g., "hardware", "support", "downloads"
                    if main_section not in domain_paths:
                        domain_paths[main_section] = 0
                    domain_paths[main_section] += 1
            
            logger.info(f"\nDocuments by Section:")
            for section, count in sorted(domain_paths.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  /{section}: {count} documents")


async def main():
    deduplicator = ContentDeduplicator()
    
    # Run audit
    await deduplicator.audit_all_brands()
    
    # Show summary
    total_dups = len(deduplicator.duplicate_docs)
    logger.info(f"\n\nSummary:")
    logger.info(f"  Total duplicate groups found: {total_dups}")
    
    if total_dups > 0:
        # Ask for confirmation before removing
        logger.info(f"\n⚠️  Found {total_dups} duplicate documents to remove")
        logger.info("Review the log above to verify duplicates")
        logger.info("To remove duplicates, uncomment the removal code below")
        
        # Uncomment to actually remove:
        # await deduplicator.remove_duplicates()
    
    # Detailed quality reports for main brands
    for brand_name in ["Allen & Heath", "RCF", "Montarbo"]:
        await deduplicator.verify_brand_quality(brand_name)


if __name__ == "__main__":
    asyncio.run(main())
