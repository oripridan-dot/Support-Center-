import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.vector_db import get_collection

def test_chroma():
    print("Getting collection...")
    collection = get_collection()
    print(f"Collection count: {collection.count()}")
    
    print("Querying collection...")
    try:
        results = collection.query(
            query_texts=["RCF 2 2 C"],
            n_results=1
        )
        print("Query successful!")
        print(results)
    except Exception as e:
        print(f"Query failed: {e}")

if __name__ == "__main__":
    test_chroma()
