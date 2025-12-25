#!/usr/bin/env python3
"""
Ingest Allen & Heath Documents to ChromaDB
Async wrapper to populate vector database with document metadata
"""
import asyncio
import logging
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand, Document
from app.services.rag_service import ingest_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-ChromaDB-Ingestion")

async def ingest_ah_documents():
    """Ingest all Allen & Heath documents to ChromaDB"""
    logger.info("=" * 80)
    logger.info("Starting ChromaDB Ingestion for Allen & Heath")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        # Get Allen & Heath brand
        brand = session.exec(select(Brand).where(Brand.name == "Allen & Heath")).first()
        if not brand:
            logger.error("Allen & Heath brand not found")
            return
        
        # Get all documents for this brand
        documents = session.exec(select(Document).where(Document.brand_id == brand.id)).all()
        logger.info(f"Found {len(documents)} Allen & Heath documents")
        
        # Ingest each document asynchronously
        success_count = 0
        failed_count = 0
        
        for doc in documents:
            try:
                # Ingest with metadata
                metadata = {
                    "brand_id": str(brand.id),
                    "brand_name": brand.name,
                    "doc_type": "official_documentation",
                    "url": doc.url,
                    "title": doc.title
                }
                
                # Use document title and URL as content for embedding
                content = f"{doc.title}\n{doc.url}"
                
                await ingest_document(
                    text=content,
                    metadata=metadata
                )
                
                success_count += 1
                logger.info(f"✓ Ingested: {doc.title}")
                
            except Exception as e:
                failed_count += 1
                logger.warning(f"✗ Failed to ingest {doc.title}: {e}")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("CHROMADB INGESTION STATUS:")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Total: {len(documents)}")
        logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(ingest_ah_documents())
