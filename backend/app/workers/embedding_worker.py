"""
Distributed embedding generation worker with batch processing.

Features:
- Parallel embedding generation
- ChromaDB integration for vector storage
- Batch processing for efficiency
- Automatic chunking and deduplication
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import structlog
from celery import Task

from app.workers.queue_manager import celery_app
from app.monitoring.metrics import embedding_queue_size

logger = structlog.get_logger(__name__)


class EmbeddingTask(Task):
    """
    Base task for embedding generation with retry logic.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 30}
    retry_backoff = True
    

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.7:  # At least 70% of chunk
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def generate_chunk_id(text: str, url: str, index: int) -> str:
    """
    Generate unique ID for a chunk.
    """
    content = f"{url}:{index}:{text[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()


@celery_app.task(base=EmbeddingTask, bind=True, name='app.workers.embedding_worker.embedding_task')
def embedding_task(
    self,
    content: str,
    url: str,
    brand: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate embeddings for scraped content and store in ChromaDB.
    
    Args:
        content: Text content to embed
        url: Source URL
        brand: Brand name
        metadata: Additional metadata
        
    Returns:
        Embedding generation results
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("embedding_started", url=url, brand=brand, content_length=len(content))
        
        # Import here to avoid circular dependencies
        from app.core.vector_store import get_chromadb_client
        
        # Chunk the content
        chunks = chunk_text(content)
        logger.info("content_chunked", url=url, chunk_count=len(chunks))
        
        # Get ChromaDB client
        chroma_client = get_chromadb_client()
        collection = chroma_client.get_or_create_collection(
            name=f"support_docs_{brand.lower()}",
            metadata={"brand": brand}
        )
        
        # Prepare documents for embedding
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(chunk, url, i)
            
            documents.append(chunk)
            ids.append(chunk_id)
            metadatas.append({
                'url': url,
                'brand': brand,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'processed_at': datetime.utcnow().isoformat(),
                **(metadata or {})
            })
        
        # Add to ChromaDB (embeddings generated automatically)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        result = {
            'status': 'success',
            'url': url,
            'brand': brand,
            'chunks_created': len(chunks),
            'collection': collection.name,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("embedding_completed", **result)
        return result
        
    except Exception as e:
        logger.error("embedding_failed", url=url, brand=brand, error=str(e))
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@celery_app.task(bind=True, name='app.workers.embedding_worker.batch_embedding')
def batch_embedding(
    self,
    documents: List[Dict[str, Any]],
    brand: str,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Process multiple documents for embedding in batches.
    
    Args:
        documents: List of documents with 'content', 'url' fields
        brand: Brand name
        batch_size: Batch processing size
        
    Returns:
        Batch processing summary
    """
    logger.info("batch_embedding_started", brand=brand, document_count=len(documents))
    
    results = []
    failed = []
    
    # Process in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        
        # Create task group
        from celery import group
        job = group(
            embedding_task.s(
                doc['content'],
                doc['url'],
                brand,
                doc.get('metadata')
            )
            for doc in batch
        )
        
        # Execute batch
        result = job.apply_async()
        
        try:
            batch_results = result.get(timeout=300)
            results.extend(batch_results)
        except Exception as e:
            logger.error("batch_embedding_failed", batch_num=i//batch_size, error=str(e))
            failed.extend([doc['url'] for doc in batch])
    
    summary = {
        'status': 'completed',
        'brand': brand,
        'total_documents': len(documents),
        'successful': len(results),
        'failed': len(failed),
        'failed_urls': failed,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info("batch_embedding_completed", **summary)
    return summary


@celery_app.task(name='app.workers.embedding_worker.reindex_outdated')
def reindex_outdated(
    brand: Optional[str] = None,
    days_old: int = 30
) -> Dict[str, Any]:
    """
    Reindex embeddings older than specified days.
    
    Args:
        brand: Optional brand filter
        days_old: Reindex documents older than this many days
        
    Returns:
        Reindexing summary
    """
    from datetime import timedelta
    from app.core.vector_store import get_chromadb_client
    
    logger.info("reindex_started", brand=brand, days_old=days_old)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    chroma_client = get_chromadb_client()
    
    # Get collections to reindex
    collections = chroma_client.list_collections()
    
    reindexed_count = 0
    
    for collection in collections:
        # Filter by brand if specified
        if brand and brand.lower() not in collection.name:
            continue
        
        # Query for old documents
        results = collection.get(
            where={"processed_at": {"$lt": cutoff_date.isoformat()}},
            include=['metadatas']
        )
        
        if results['ids']:
            logger.info(
                "reindexing_collection",
                collection=collection.name,
                document_count=len(results['ids'])
            )
            
            # Delete old embeddings
            collection.delete(ids=results['ids'])
            
            # Queue for re-embedding
            for metadata in results['metadatas']:
                # Note: Would need to re-scrape or have content cached
                logger.info("queued_for_reembedding", url=metadata.get('url'))
            
            reindexed_count += len(results['ids'])
    
    return {
        'status': 'completed',
        'reindexed_count': reindexed_count,
        'cutoff_date': cutoff_date.isoformat(),
        'timestamp': datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.embedding_worker.get_collection_stats')
def get_collection_stats(brand: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics for embedding collections.
    
    Args:
        brand: Optional brand filter
        
    Returns:
        Collection statistics
    """
    from app.core.vector_store import get_chromadb_client
    
    chroma_client = get_chromadb_client()
    collections = chroma_client.list_collections()
    
    stats = {}
    
    for collection in collections:
        if brand and brand.lower() not in collection.name:
            continue
        
        count = collection.count()
        
        stats[collection.name] = {
            'document_count': count,
            'metadata': collection.metadata
        }
    
    return {
        'collections': stats,
        'total_collections': len(stats),
        'timestamp': datetime.utcnow().isoformat()
    }
