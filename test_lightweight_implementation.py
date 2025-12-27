"""
Test script to verify the new lightweight implementation
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/workspaces/Support-Center-/backend')

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from app.workers.task_queue import task_queue, SimpleTaskQueue, Task
        print("   ✅ Task queue imports successful")
    except Exception as e:
        print(f"   ❌ Task queue import failed: {e}")
        return False
    
    try:
        from app.core.cache import cache, cached, SimpleCache
        print("   ✅ Cache imports successful")
    except Exception as e:
        print(f"   ❌ Cache import failed: {e}")
        return False
    
    try:
        from app.scrapers.smart_scraper import SmartScraper, scrape_urls
        print("   ✅ Smart scraper imports successful")
    except Exception as e:
        print(f"   ❌ Smart scraper import failed: {e}")
        return False
    
    try:
        from app.monitoring.simple_metrics import metrics, MetricsCollector
        print("   ✅ Metrics imports successful")
    except Exception as e:
        print(f"   ❌ Metrics import failed: {e}")
        return False
    
    try:
        from app.api.async_endpoints import router
        print("   ✅ API endpoints imports successful")
    except Exception as e:
        print(f"   ❌ API endpoints import failed: {e}")
        return False
    
    return True


async def test_task_queue():
    """Test task queue functionality"""
    print("\n🧪 Testing task queue...")
    
    from app.workers.task_queue import SimpleTaskQueue
    
    # Create test queue
    queue = SimpleTaskQueue(num_workers=2)
    await queue.start()
    
    # Define test function
    def test_func(x, y):
        return x + y
    
    # Add task
    task_id = await queue.add_task(
        task_id="test_task_1",
        func=test_func,
        args=(5, 3),
        priority=1
    )
    
    print(f"   📝 Added task: {task_id}")
    
    # Wait for completion
    await asyncio.sleep(2)
    
    # Check result
    result = queue.get_result(task_id)
    
    if result.get('status') == 'completed' and result.get('result') == 8:
        print(f"   ✅ Task completed successfully: {result['result']}")
        success = True
    else:
        print(f"   ❌ Task failed or incomplete: {result}")
        success = False
    
    # Check queue status
    status = queue.get_queue_status()
    print(f"   📊 Queue status: {status}")
    
    await queue.stop()
    
    return success


def test_cache():
    """Test cache functionality"""
    print("\n🧪 Testing cache...")
    
    from app.core.cache import SimpleCache
    
    # Create test cache
    cache_dir = "/tmp/test_cache"
    cache = SimpleCache(cache_dir=cache_dir)
    
    # Test set/get
    cache.set("test_key", {"data": "test_value"})
    result = cache.get("test_key", max_age_seconds=60)
    
    if result and result.get('data') == 'test_value':
        print("   ✅ Cache set/get works")
        success = True
    else:
        print(f"   ❌ Cache failed: {result}")
        success = False
    
    # Test stats
    stats = cache.get_stats()
    print(f"   📊 Cache stats: hits={stats['cache_hits']}, misses={stats['cache_misses']}")
    
    # Cleanup
    cache.clear_all()
    
    return success


def test_metrics():
    """Test metrics functionality"""
    print("\n🧪 Testing metrics...")
    
    from app.monitoring.simple_metrics import MetricsCollector
    
    # Create test metrics
    metrics_file = "/tmp/test_metrics.jsonl"
    metrics = MetricsCollector(log_file=metrics_file)
    
    # Record some metrics
    metrics.record(
        endpoint="/test",
        method="GET",
        status_code=200,
        duration_ms=123.45
    )
    
    metrics.record(
        endpoint="/test2",
        method="POST",
        status_code=201,
        duration_ms=456.78
    )
    
    # Get stats
    stats = metrics.get_stats(last_n=10)
    
    if stats['total_requests'] == 2:
        print(f"   ✅ Metrics recording works: {stats['total_requests']} requests")
        success = True
    else:
        print(f"   ❌ Metrics failed: {stats}")
        success = False
    
    print(f"   📊 Average duration: {stats['avg_duration_ms']}ms")
    
    # Cleanup
    if os.path.exists(metrics_file):
        os.remove(metrics_file)
    
    return success


def test_decorator():
    """Test cache decorator"""
    print("\n🧪 Testing cache decorator...")
    
    from app.core.cache import cached, SimpleCache
    import time
    
    cache = SimpleCache(cache_dir="/tmp/test_decorator_cache")
    
    call_count = 0
    
    @cached(max_age=60)
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        time.sleep(0.1)  # Simulate expensive operation
        return x * 2
    
    # First call (should execute)
    result1 = expensive_function(5)
    calls_after_first = call_count
    
    # Second call (should use cache)
    result2 = expensive_function(5)
    calls_after_second = call_count
    
    if result1 == 10 and result2 == 10 and calls_after_second == calls_after_first:
        print(f"   ✅ Cache decorator works (function called {call_count} time, returned {result1} twice)")
        success = True
    else:
        print(f"   ❌ Decorator failed: calls={call_count}, results={result1}, {result2}")
        success = False
    
    return success


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Testing Lightweight Implementation")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test task queue
    results.append(("Task Queue", await test_task_queue()))
    
    # Test cache
    results.append(("Cache", test_cache()))
    
    # Test metrics
    results.append(("Metrics", test_metrics()))
    
    # Test decorator
    results.append(("Decorator", test_decorator()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
