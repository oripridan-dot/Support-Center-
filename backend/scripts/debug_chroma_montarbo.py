import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("support_docs")

results = collection.query(
    query_texts=["B115"],
    where={"brand_id": 50},
    n_results=3
)

print("Found documents:", len(results['documents'][0]))
for i, doc in enumerate(results['documents'][0]):
    print(f"\n--- Document {i+1} ---")
    print(doc[:200] + "...")
    print("Metadata:", results['metadatas'][0][i])
