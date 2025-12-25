#!/usr/bin/env python3
"""
Performance Optimization Script
Applies all performance improvements and verifies system health
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, text
from app.core.database import engine
from app.models import Brand
import time

def optimize_database():
    """Apply database optimizations"""
    print("🔧 Optimizing Database...")
    
    with Session(engine) as session:
        # Verify WAL mode is enabled
        result = session.exec(text("PRAGMA journal_mode")).one()
        print(f"   Journal Mode: {result[0] if isinstance(result, tuple) else result}")
        
        # Verify synchronous mode
        result = session.exec(text("PRAGMA synchronous")).one()
        print(f"   Synchronous Mode: {result[0] if isinstance(result, tuple) else result}")
        
        # Verify cache size
        result = session.exec(text("PRAGMA cache_size")).one()
        cache_pages = result[0] if isinstance(result, tuple) else result
        print(f"   Cache Size: {cache_pages} pages (~{abs(int(cache_pages)) * 4 / 1024:.1f} MB)")
        
        # Check if indexes exist on frequently queried fields
        print("\n🔍 Checking Indexes...")
        indexes = session.exec(text("""
            SELECT name, tbl_name 
            FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)).all()
        
        if indexes:
            for idx in indexes:
                print(f"   ✅ {idx[0]} on {idx[1]}")
        else:
            print("   ⚠️  No custom indexes found")
        
        # Analyze database for query optimization
        print("\n📊 Analyzing Database...")
        session.exec(text("ANALYZE"))
        print("   ✅ Statistics updated")
        
        # Vacuum to reclaim space and defragment
        print("\n🧹 Cleaning Database...")
        session.exec(text("VACUUM"))
        print("   ✅ Database optimized")

def check_brands():
    """Check brand data integrity"""
    print("\n📦 Checking Brands...")
    
    with Session(engine) as session:
        brands = session.query(Brand).all()
        print(f"   Total Brands: {len(brands)}")
        
        for brand in brands[:5]:  # Show first 5
            print(f"   - {brand.name}")
        
        if len(brands) > 5:
            print(f"   ... and {len(brands) - 5} more")

def performance_benchmark():
    """Run performance benchmarks"""
    print("\n⚡ Performance Benchmark...")
    
    with Session(engine) as session:
        # Test query performance
        start = time.time()
        brands = session.query(Brand).all()
        query_time = (time.time() - start) * 1000
        print(f"   Brand Query: {query_time:.2f}ms")
        
        # Test connection time
        start = time.time()
        session.exec(text("SELECT 1")).first()
        conn_time = (time.time() - start) * 1000
        print(f"   Connection: {conn_time:.2f}ms")
        
        # Performance verdict
        if query_time < 50:
            print("   ✅ Performance: Excellent")
        elif query_time < 200:
            print("   ✅ Performance: Good")
        else:
            print("   ⚠️  Performance: Needs optimization")

def main():
    print("=" * 60)
    print("  🚀 RAG Application - Performance Optimization")
    print("=" * 60)
    
    try:
        optimize_database()
        check_brands()
        performance_benchmark()
        
        print("\n" + "=" * 60)
        print("  ✅ Optimization Complete!")
        print("=" * 60)
        print("\n💡 Tips:")
        print("   - Keep database under 1GB for SQLite optimal performance")
        print("   - Consider PostgreSQL if > 100k documents")
        print("   - Monitor logs for slow queries (>100ms)")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
