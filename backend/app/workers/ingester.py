"""
Ingester Worker

Responsibilities:
- Receives scraped documents from Scraper
- Chunks documents into optimal sizes for vectorization
- Generates embeddings and stores in ChromaDB
- Updates database with document records
- Calls Explorer for verification after ingestion completes

The Ingester is the final stage that makes documents searchable through RAG.
"""

import asyncio
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.sql_models import Brand, Document
from app.workers.scraper import ScrapedDocument
from app.workers.explorer import ExplorerWorker


class IngesterWorker:
    """
    Vectorizes and indexes scraped documentation.
    
    MISSION: Make every document searchable and verify 100% coverage.
    Calls Explorer to verify we didn't miss anything.
    """
    
    def __init__(self):
        self.explorer = ExplorerWorker()
    
    async def ingest_batch(
        self, 
        scraped_docs: List[ScrapedDocument],
        brand_id: int,
        verify: bool = True
    ) -> Dict:
        """
        Main ingestion method - vectorizes and stores documents
        """
        brand_name = scraped_docs[0].brand_name if scraped_docs else "Unknown"
        print(f"📥 [INGESTER] Starting ingestion for {brand_name}")
        print(f"  📄 Documents to ingest: {len(scraped_docs)}")
        
        # Update status tracker
        from app.workers.status_tracker import worker_status
        worker_status.ingester_start(brand_id, brand_name, len(scraped_docs))
        
        session = next(get_session())
        ingested_count = 0
        skipped_count = 0
        error_count = 0
        
        for idx, scraped_doc in enumerate(scraped_docs, 1):
            try:
                # Log to status tracker
                from app.workers.status_tracker import worker_status
                worker_status._log(f"📥 Indexing: {scraped_doc.title[:50]}...")
                
                print(f"  [{idx}/{len(scraped_docs)}] Processing: {scraped_doc.title}")
                
                # Check if document already exists
                existing = session.exec(
                    select(Document).where(Document.url == scraped_doc.url)
                ).first()
                
                if existing:
                    print(f"    ⏭️  Skipping (already exists): {scraped_doc.url}")
                    worker_status._log(f"⏭️ Skipped: {scraped_doc.title} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create database record
                doc = Document(
                    brand_id=brand_id,
                    title=scraped_doc.title,
                    content=scraped_doc.content,
                    url=scraped_doc.url,
                    doc_type=scraped_doc.doc_type or "manual",
                    file_path=scraped_doc.file_path,
                    created_at=datetime.now()
                )
                
                session.add(doc)
                session.commit()
                session.refresh(doc)
                
                # Vectorize and store in ChromaDB
                chunks_ingested = await self._vectorize_document(doc, brand_id, brand_name)
                
                if chunks_ingested > 0:
                    ingested_count += 1
                    print(f"    ✅ Ingested: {chunks_ingested} chunks")
                    worker_status._log(f"✅ Indexed: {scraped_doc.title} ({chunks_ingested} chunks)")
                    
                    # Update progress
                    progress = int((idx / len(scraped_docs)) * 100)
                    worker_status.ingester_progress(
                        f"Indexed {idx}/{len(scraped_docs)} docs",
                        progress,
                        ingested_count,
                        chunks_ingested
                    )
                else:
                    error_count += 1
                    print(f"    ❌ Failed to vectorize")
                
            except Exception as e:
                error_count += 1
                print(f"    ❌ Error ingesting {scraped_doc.title}: {e}")
                continue
        
        print(f"\n{'='*70}")
        print(f"📊 INGESTION REPORT: {brand_name}")
        print(f"{'='*70}")
        print(f"✅ INDEXED:    {ingested_count} documents")
        print(f"⏭️  SKIPPED:    {skipped_count} documents (already existed)")
        print(f"❌ ERRORS:     {error_count} documents")
        print(f"{'='*70}")
        
        # Verify ingestion against Explorer's discovery
        verification_report = None
        if verify:
            print(f"\n🔍 [INGESTER] Calling Explorer for COVERAGE VERIFICATION...")
            try:
                verification_report = await self.explorer.verify_ingestion(brand_id)
                
                # Update status tracker with final coverage
                from app.workers.status_tracker import worker_status
                coverage = verification_report.coverage_percentage if verification_report else 0
                worker_status.ingester_complete(ingested_count, error_count, coverage)
                
                # If coverage < 100%, flag it loudly
                if verification_report and verification_report.coverage_percentage < 100:
                    print(f"\n⚠️  ⚠️  ⚠️  WARNING: INCOMPLETE COVERAGE ⚠️  ⚠️  ⚠️")
                    print(f"Missing {len(verification_report.missing_docs)} documents!")
                    print(f"Action required: Re-run pipeline or manual intervention.\n")
            except Exception as e:
                print(f"⚠️  Verification failed: {e}")
        
        return {
            "ingested": ingested_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total": len(scraped_docs),
            "verification_report": verification_report.model_dump() if verification_report else None
        }
    
    async def _vectorize_document(
        self, 
        doc: Document, 
        brand_id: int,
        brand_name: str
    ) -> int:
        """
        Chunk and vectorize a single document
        """
        try:
            # Use the ingest_document function from rag_service
            from app.services.rag_service import ingest_document
            
            # Create metadata
            metadata = {
                "brand_id": str(brand_id),
                "brand_name": brand_name,
                "doc_id": str(doc.id),
                "title": doc.title,
                "url": doc.url or "",
                "doc_type": doc.doc_type or "manual"
            }
            
            # Ingest document
            await ingest_document(
                text=doc.content,
                metadata=metadata,
                document_id=f"doc_{doc.id}"
            )
            
            # Estimate chunks (rough approximation)
            chunks = len(doc.content) // 500  # Assuming 500 chars per chunk
            return chunks if chunks > 0 else 1
        except Exception as e:
            print(f"    ❌ Vectorization error: {e}")
            return 0
    
    async def reindex_brand(self, brand_id: int) -> Dict:
        """
        Re-vectorize all documents for a brand (useful after schema changes)
        """
        print(f"🔄 [INGESTER] Starting re-indexing for brand {brand_id}")
        
        session = next(get_session())
        
        # Get brand
        brand = session.exec(select(Brand).where(Brand.id == brand_id)).first()
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")
        
        # Get all documents
        docs = session.exec(
            select(Document).where(Document.brand_id == brand_id)
        ).all()
        
        print(f"  📄 Found {len(docs)} documents to re-index")
        
        # Clear existing vectors (optional - depends on requirements)
        # TODO: Implement ChromaDB collection clearing for brand
        
        # Re-vectorize all
        ingested_count = 0
        for doc in docs:
            chunks = await self._vectorize_document(doc, brand_id, brand.name)
            if chunks > 0:
                ingested_count += 1
        
        print(f"✅ [INGESTER] Re-indexing complete: {ingested_count}/{len(docs)} documents")
        
        return {
            "reindexed": ingested_count,
            "total": len(docs)
        }
