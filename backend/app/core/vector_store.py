"""
Vector store utilities for ChromaDB integration.
"""

import os
import chromadb
from chromadb.config import Settings
import structlog

logger = structlog.get_logger(__name__)

# ChromaDB client singleton
_chromadb_client = None


def get_chromadb_client():
    """
    Get or create ChromaDB client instance.
    
    Returns:
        ChromaDB client
    """
    global _chromadb_client
    
    if _chromadb_client is None:
        try:
            chroma_host = os.getenv('CHROMA_HOST', 'localhost')
            chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
            
            # Try to connect to remote ChromaDB server
            try:
                _chromadb_client = chromadb.HttpClient(
                    host=chroma_host,
                    port=chroma_port,
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
                # Test connection
                _chromadb_client.heartbeat()
                logger.info("chromadb_connected", host=chroma_host, port=chroma_port)
                
            except Exception as e:
                logger.warning("chromadb_remote_failed", error=str(e))
                
                # Fallback to persistent local client
                persist_directory = os.getenv('CHROMA_PERSIST_DIR', '/workspaces/Support-Center-/backend/chroma_db')
                
                _chromadb_client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
                logger.info("chromadb_local_initialized", path=persist_directory)
                
        except Exception as e:
            logger.error("chromadb_initialization_failed", error=str(e))
            raise
    
    return _chromadb_client


def create_collection(
    name: str,
    metadata: dict = None
):
    """
    Create a new ChromaDB collection.
    
    Args:
        name: Collection name
        metadata: Optional metadata
        
    Returns:
        ChromaDB collection
    """
    client = get_chromadb_client()
    
    try:
        collection = client.create_collection(
            name=name,
            metadata=metadata or {}
        )
        logger.info("collection_created", name=name, metadata=metadata)
        return collection
        
    except Exception as e:
        logger.error("collection_creation_failed", name=name, error=str(e))
        raise


def get_or_create_collection(
    name: str,
    metadata: dict = None
):
    """
    Get existing collection or create if doesn't exist.
    
    Args:
        name: Collection name
        metadata: Optional metadata
        
    Returns:
        ChromaDB collection
    """
    client = get_chromadb_client()
    
    try:
        collection = client.get_or_create_collection(
            name=name,
            metadata=metadata or {}
        )
        return collection
        
    except Exception as e:
        logger.error("get_or_create_collection_failed", name=name, error=str(e))
        raise
