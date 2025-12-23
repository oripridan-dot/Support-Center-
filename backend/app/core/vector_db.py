import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
# For development, we use a local persistent directory.
# In production, this might connect to a server.
client = chromadb.PersistentClient(path="./chroma_db")

def get_collection(name: str = "support_docs"):
    return client.get_or_create_collection(name=name)
