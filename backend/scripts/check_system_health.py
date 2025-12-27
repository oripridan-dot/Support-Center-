#!/usr/bin/env python3
"""
System Health Check and Data Verification
Scans database, vector store, and API to ensure all systems are synced
"""

import sqlite3
import sys
from pathlib import Path

def check_database():
    """Check SQL database statistics"""
    print("=" * 80)
    print("DATABASE HEALTH CHECK")
    print("=" * 80)
    
    db_path = Path("support_center.db")
    if not db_path.exists():
        print("❌ Database not found!")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute("SELECT COUNT(*) FROM brand")
    brand_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM document")
    doc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM product")
    product_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM productfamily")
    family_count = cursor.fetchone()[0]
    
    print(f"\n✅ Database: support_center.db")
    print(f"   Brands:          {brand_count:>6}")
    print(f"   Documents:       {doc_count:>6}")
    print(f"   Products:        {product_count:>6}")
    print(f"   Product Families:{family_count:>6}")
    
    # Top brands
    print(f"\n📊 Top 10 Brands by Documentation:")
    cursor.execute("""
        SELECT b.name, COUNT(d.id) as doc_count
        FROM brand b
        LEFT JOIN document d ON d.brand_id = b.id
        GROUP BY b.id, b.name
        ORDER BY doc_count DESC
        LIMIT 10
    """)
    
    for i, (name, count) in enumerate(cursor.fetchall(), 1):
        print(f"   {i:2}. {name:<30} {count:>5} docs")
    
    conn.close()
    return True

def check_vector_store():
    """Check ChromaDB vector store"""
    print("\n" + "=" * 80)
    print("VECTOR STORE HEALTH CHECK")
    print("=" * 80)
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        
        print(f"\n✅ ChromaDB initialized")
        print(f"   Collections: {len(collections)}")
        
        for collection in collections:
            count = collection.count()
            print(f"\n📦 Collection: {collection.name}")
            print(f"   Vectors: {count:,}")
            
            # Sample metadata
            if count > 0:
                sample = collection.peek(limit=1)
                if sample and sample.get('metadatas') and len(sample['metadatas']) > 0:
                    metadata = sample['metadatas'][0]
                    print(f"   Metadata fields: {', '.join(metadata.keys())}")
                    if 'brand_id' in metadata:
                        print(f"   ✅ Brand filtering available")
                    if 'product_id' in metadata:
                        print(f"   ✅ Product filtering available")
        
        return True
    except Exception as e:
        print(f"❌ Vector store error: {e}")
        return False

def check_data_consistency():
    """Check data consistency between DB and vector store"""
    print("\n" + "=" * 80)
    print("DATA CONSISTENCY CHECK")
    print("=" * 80)
    
    conn = sqlite3.connect("support_center.db")
    cursor = conn.cursor()
    
    # Count documents in DB
    cursor.execute("SELECT COUNT(*) FROM document")
    db_docs = cursor.fetchone()[0]
    
    # Count vectors in ChromaDB
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection("support_docs")
        vector_count = collection.count()
        
        print(f"\n📊 Document Counts:")
        print(f"   SQL Database:  {db_docs:>6} documents")
        print(f"   Vector Store:  {vector_count:>6} vectors")
        
        # Vectors can be more than docs (chunked)
        if vector_count >= db_docs:
            ratio = vector_count / db_docs if db_docs > 0 else 0
            print(f"   Chunk Ratio:   {ratio:>6.2f}x (vectors per document)")
            print(f"   ✅ Data is consistent (vectors >= documents)")
        else:
            print(f"   ⚠️  Warning: Fewer vectors than documents")
            print(f"   Consider re-indexing the vector store")
        
    except Exception as e:
        print(f"❌ Could not compare: {e}")
    
    conn.close()

def check_recent_activity():
    """Check recent ingestion activity"""
    print("\n" + "=" * 80)
    print("RECENT ACTIVITY")
    print("=" * 80)
    
    conn = sqlite3.connect("support_center.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            b.name,
            MAX(d.last_updated) as latest_doc,
            COUNT(d.id) as doc_count
        FROM brand b
        JOIN document d ON d.brand_id = b.id
        GROUP BY b.id, b.name
        ORDER BY latest_doc DESC
        LIMIT 10
    """)
    
    print(f"\n📅 Recently Updated Brands:")
    for name, last_update, count in cursor.fetchall():
        timestamp = last_update[:19] if last_update else "Unknown"
        print(f"   {name:<30} {count:>4} docs - Last: {timestamp}")
    
    conn.close()

def main():
    print("\n" + "=" * 80)
    print("HALILIT SUPPORT CENTER - SYSTEM HEALTH CHECK")
    print("=" * 80)
    print()
    
    checks = [
        ("Database", check_database),
        ("Vector Store", check_vector_store),
        ("Data Consistency", check_data_consistency),
        ("Recent Activity", check_recent_activity),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    all_pass = all(r[1] for r in results if r[1] is not None)
    if all_pass:
        print("\n🎉 All systems operational!")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
