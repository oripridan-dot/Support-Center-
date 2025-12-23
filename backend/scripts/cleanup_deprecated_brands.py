#!/usr/bin/env python3
"""
Clean up deprecated brands: DB Technologies, Marshall, Ampeg, Spector
This script removes:
1. Brand records from SQL database
2. All associated documents
3. All associated data from ChromaDB
"""

import asyncio
import logging
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document, Product, ProductFamily
from app.core.vector_db import get_collection
from sqlmodel import select

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cleanup_deprecated_brands.log")
    ]
)

logger = logging.getLogger("DeprecatedBrandCleanup")

BRANDS_TO_DROP = ["Marshall", "Ampeg", "Spector", "dBTechnologies"]


def cleanup_sql_database():
    """Remove brands and associated records from SQL database."""
    logger.info("Starting SQL database cleanup...")
    
    with Session(engine) as session:
        for brand_name in BRANDS_TO_DROP:
            try:
                brand = session.exec(
                    select(Brand).where(Brand.name == brand_name)
                ).first()
                
                if not brand:
                    logger.warning(f"Brand '{brand_name}' not found in database")
                    continue
                
                brand_id = brand.id
                
                # Delete all documents for this brand
                docs = session.exec(
                    select(Document).where(Document.brand_id == brand_id)
                ).all()
                doc_count = len(docs)
                
                for doc in docs:
                    session.delete(doc)
                
                # Delete all products for this brand (and their associations)
                families = session.exec(
                    select(ProductFamily).where(ProductFamily.brand_id == brand_id)
                ).all()
                
                family_count = 0
                for family in families:
                    products = session.exec(
                        select(Product).where(Product.family_id == family.id)
                    ).all()
                    for product in products:
                        session.delete(product)
                    session.delete(family)
                    family_count += 1
                
                # Delete the brand itself
                session.delete(brand)
                session.commit()
                
                logger.info(
                    f"✓ Dropped brand '{brand_name}' (ID: {brand_id}) "
                    f"- Removed {doc_count} documents, {family_count} families"
                )
                
            except Exception as e:
                logger.error(f"✗ Error dropping '{brand_name}': {e}")
                session.rollback()


def cleanup_chromadb():
    """Remove brand data from ChromaDB."""
    logger.info("Starting ChromaDB cleanup...")
    
    try:
        collection = get_collection()
        
        for brand_name in BRANDS_TO_DROP:
            # Get brand ID from database to filter in ChromaDB
            with Session(engine) as session:
                brand = session.exec(
                    select(Brand).where(Brand.name == brand_name)
                ).first()
                
                if not brand:
                    logger.warning(f"Brand '{brand_name}' not found for ChromaDB cleanup")
                    continue
                
                # Query and delete all documents with this brand_id from ChromaDB
                try:
                    results = collection.get(
                        where={"brand_id": brand.id},
                        include=[]
                    )
                    
                    if results['ids']:
                        collection.delete(ids=results['ids'])
                        logger.info(
                            f"✓ Removed {len(results['ids'])} vectors for '{brand_name}' from ChromaDB"
                        )
                    else:
                        logger.info(f"No ChromaDB entries found for '{brand_name}'")
                        
                except Exception as e:
                    logger.warning(f"Could not delete from ChromaDB for '{brand_name}': {e}")
                    
    except Exception as e:
        logger.error(f"ChromaDB cleanup failed: {e}")


def verify_cleanup():
    """Verify that brands have been removed."""
    logger.info("Verifying cleanup...")
    
    with Session(engine) as session:
        for brand_name in BRANDS_TO_DROP:
            brand = session.exec(
                select(Brand).where(Brand.name == brand_name)
            ).first()
            
            if brand:
                logger.error(f"✗ Brand '{brand_name}' still exists in database!")
            else:
                logger.info(f"✓ Brand '{brand_name}' successfully removed")


async def main():
    logger.info("=" * 70)
    logger.info("Starting cleanup of deprecated brands")
    logger.info(f"Brands to remove: {', '.join(BRANDS_TO_DROP)}")
    logger.info("=" * 70)
    
    cleanup_sql_database()
    cleanup_chromadb()
    verify_cleanup()
    
    logger.info("=" * 70)
    logger.info("Cleanup complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
