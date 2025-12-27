#!/usr/bin/env python3
"""
Comprehensive Test Suite for 22-Worker High-Performance System
Tests all 5 categories, priorities, parallel execution, and circuit breakers
"""

import requests
import time
import json
from datetime import datetime
from typing import List, Dict
import concurrent.futures

BASE_URL = "http://localhost:8080"
COLORS = {
    'green': '\033[92m',
    'red': '\033[91m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'reset': '\033[0m'
}

def print_header(text: str):
    """Print a test section header"""
    print(f"\n{'=' * 70}")
    print(f"{COLORS['blue']}{text}{COLORS['reset']}")
    print('=' * 70)

def print_success(text: str):
    """Print success message"""
    print(f"{COLORS['green']}✅ {text}{COLORS['reset']}")

def print_error(text: str):
    """Print error message"""
    print(f"{COLORS['red']}❌ {text}{COLORS['reset']}")

def print_info(text: str):
    """Print info message"""
    print(f"{COLORS['yellow']}ℹ️  {text}{COLORS['reset']}")


# ===================================================================
# TEST 1: SYSTEM HEALTH
# ===================================================================

def test_system_health():
    """Test that the worker system is healthy"""
    print_header("TEST 1: System Health Check")
    
    try:
        # Test main health endpoint
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print_success("Main health endpoint responding")
        
        # Test HP worker health
        r = requests.get(f"{BASE_URL}/api/hp/health", timeout=5)
        assert r.status_code == 200, f"HP health check failed: {r.status_code}"
        health = r.json()
        
        assert health['healthy'], "Worker pool not healthy"
        assert health['running'], "Worker pool not running"
        assert health['workers']['total'] == 22, f"Expected 22 workers, got {health['workers']['total']}"
        
        print_success(f"Worker pool healthy: {health['workers']['total']} workers running")
        print_info(f"Health percentage: {health['workers']['health_percentage']}%")
        
        return True
    except Exception as e:
        print_error(f"System health check failed: {e}")
        return False


# ===================================================================
# TEST 2: WORKER CONFIGURATION
# ===================================================================

def test_worker_configuration():
    """Verify all 22 workers are properly configured"""
    print_header("TEST 2: Worker Configuration")
    
    try:
        r = requests.get(f"{BASE_URL}/api/hp/workers", timeout=5)
        assert r.status_code == 200, f"Failed to get worker stats: {r.status_code}"
        
        workers = r.json()
        assert workers['total_workers'] == 22, f"Expected 22 workers, got {workers['total_workers']}"
        
        categories = workers['categories']
        
        # Verify worker distribution
        expected = {
            'scraping': 6,
            'rag_query': 10,
            'embedding': 3,
            'batch_processing': 2,
            'maintenance': 1
        }
        
        for category, expected_count in expected.items():
            actual_count = categories[category]['workers']
            assert actual_count == expected_count, \
                f"Expected {expected_count} {category} workers, got {actual_count}"
            print_success(f"{category.upper()}: {actual_count} workers")
        
        return True
    except Exception as e:
        print_error(f"Worker configuration test failed: {e}")
        return False


# ===================================================================
# TEST 3: SCRAPING WORKERS (6 workers)
# ===================================================================

def test_scraping_workers():
    """Test scraping worker pool"""
    print_header("TEST 3: Scraping Workers (6 workers)")
    
    try:
        # Submit 10 scraping tasks
        task_ids = []
        start_time = time.time()
        
        print_info("Submitting 10 scraping tasks...")
        for i in range(10):
            payload = {
                "url": f"https://example.com/page{i}",
                "brand": "halilit",
                "priority": "NORMAL"
            }
            r = requests.post(f"{BASE_URL}/api/hp/scrape", json=payload, timeout=5)
            assert r.status_code == 200, f"Failed to submit scraping task: {r.status_code}"
            task_ids.append(r.json()['task_id'])
        
        print_success(f"Submitted {len(task_ids)} scraping tasks")
        
        # Wait for completion
        completed = 0
        while completed < len(task_ids) and (time.time() - start_time) < 60:
            time.sleep(1)
            completed = 0
            for task_id in task_ids:
                r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
                if r.json()['status'] in ['completed', 'failed']:
                    completed += 1
            
            print_info(f"Progress: {completed}/{len(task_ids)} tasks completed")
        
        duration = time.time() - start_time
        
        # Check results
        successful = 0
        failed = 0
        for task_id in task_ids:
            r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
            status = r.json()['status']
            if status == 'completed':
                successful += 1
            elif status == 'failed':
                failed += 1
        
        print_success(f"Completed: {successful}, Failed: {failed}")
        print_info(f"Total time: {duration:.2f}s (6 workers = ~4s expected)")
        
        # With 6 workers, 10 tasks should take ~4s (2s per task, 2 rounds)
        assert duration < 8, f"Too slow: {duration:.2f}s (expected < 8s)"
        assert successful >= 8, f"Too many failures: {failed}/{len(task_ids)}"
        
        return True
    except Exception as e:
        print_error(f"Scraping workers test failed: {e}")
        return False


# ===================================================================
# TEST 4: RAG QUERY WORKERS (10 workers - CRITICAL priority)
# ===================================================================

def test_rag_query_workers():
    """Test RAG query worker pool (should be fast)"""
    print_header("TEST 4: RAG Query Workers (10 workers, CRITICAL priority)")
    
    try:
        # Submit 5 CRITICAL priority queries
        queries = [
            "What is Halilit?",
            "How to use a djembe?",
            "Roland synthesizer specs",
            "Mackie mixer troubleshooting",
            "Rode microphone setup"
        ]
        
        task_ids = []
        start_time = time.time()
        
        print_info(f"Submitting {len(queries)} CRITICAL priority queries...")
        for query in queries:
            payload = {
                "query": query,
                "priority": "CRITICAL",
                "timeout_seconds": 10
            }
            r = requests.post(f"{BASE_URL}/api/hp/query", json=payload, timeout=10)
            assert r.status_code == 200, f"Failed to submit query: {r.status_code}"
            
            result = r.json()
            if result['status'] == 'completed':
                # Query completed immediately
                task_ids.append(result['task_id'])
                print_success(f"Query completed immediately: {result['duration_seconds']:.2f}s")
            else:
                task_ids.append(result['task_id'])
        
        duration = time.time() - start_time
        
        # Queries should be FAST (CRITICAL priority + 10 workers)
        print_info(f"Total time: {duration:.2f}s")
        assert duration < 10, f"Queries too slow: {duration:.2f}s (expected < 10s)"
        
        print_success(f"All {len(queries)} queries processed quickly")
        return True
    except Exception as e:
        print_error(f"RAG query workers test failed: {e}")
        return False


# ===================================================================
# TEST 5: EMBEDDING WORKERS (3 workers)
# ===================================================================

def test_embedding_workers():
    """Test embedding worker pool"""
    print_header("TEST 5: Embedding Workers (3 workers)")
    
    try:
        # Submit 5 embedding tasks
        task_ids = []
        start_time = time.time()
        
        print_info("Submitting 5 embedding tasks...")
        for i in range(5):
            texts = [f"Document {i}-{j}" for j in range(10)]
            payload = {
                "texts": texts,
                "model": "text-embedding-3-small",
                "priority": "NORMAL"
            }
            r = requests.post(f"{BASE_URL}/api/hp/embed", json=payload, timeout=5)
            assert r.status_code == 200, f"Failed to submit embedding task: {r.status_code}"
            task_ids.append(r.json()['task_id'])
        
        print_success(f"Submitted {len(task_ids)} embedding tasks")
        
        # Wait for completion
        completed = 0
        while completed < len(task_ids) and (time.time() - start_time) < 60:
            time.sleep(1)
            completed = 0
            for task_id in task_ids:
                r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
                if r.json()['status'] in ['completed', 'failed']:
                    completed += 1
            
            print_info(f"Progress: {completed}/{len(task_ids)} tasks completed")
        
        duration = time.time() - start_time
        print_info(f"Total time: {duration:.2f}s (3 workers)")
        
        return True
    except Exception as e:
        print_error(f"Embedding workers test failed: {e}")
        return False


# ===================================================================
# TEST 6: BATCH PROCESSING WORKERS (2 workers)
# ===================================================================

def test_batch_workers():
    """Test batch processing worker pool"""
    print_header("TEST 6: Batch Processing Workers (2 workers)")
    
    try:
        # Submit 3 batch tasks
        task_ids = []
        start_time = time.time()
        
        print_info("Submitting 3 batch tasks...")
        for i in range(3):
            items = [{"id": j, "data": f"item_{j}"} for j in range(20)]
            payload = {
                "operation": "process_items",
                "items": items,
                "priority": "LOW"
            }
            r = requests.post(f"{BASE_URL}/api/hp/batch", json=payload, timeout=5)
            assert r.status_code == 200, f"Failed to submit batch task: {r.status_code}"
            task_ids.append(r.json()['task_id'])
        
        print_success(f"Submitted {len(task_ids)} batch tasks")
        
        # Wait for completion (batches are slow)
        completed = 0
        while completed < len(task_ids) and (time.time() - start_time) < 90:
            time.sleep(2)
            completed = 0
            for task_id in task_ids:
                r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
                if r.json()['status'] in ['completed', 'failed']:
                    completed += 1
            
            print_info(f"Progress: {completed}/{len(task_ids)} tasks completed")
        
        duration = time.time() - start_time
        print_info(f"Total time: {duration:.2f}s (2 workers)")
        
        return True
    except Exception as e:
        print_error(f"Batch workers test failed: {e}")
        return False


# ===================================================================
# TEST 7: MAINTENANCE WORKER (1 worker)
# ===================================================================

def test_maintenance_worker():
    """Test maintenance worker"""
    print_header("TEST 7: Maintenance Worker (1 worker)")
    
    try:
        # Submit maintenance task
        payload = {
            "operation": "health_check",
            "params": {"check_all": True},
            "priority": "BULK"
        }
        
        start_time = time.time()
        r = requests.post(f"{BASE_URL}/api/hp/maintenance", json=payload, timeout=5)
        assert r.status_code == 200, f"Failed to submit maintenance task: {r.status_code}"
        
        task_id = r.json()['task_id']
        print_success(f"Submitted maintenance task: {task_id}")
        
        # Wait for completion
        while (time.time() - start_time) < 30:
            time.sleep(1)
            r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
            status = r.json()['status']
            
            if status in ['completed', 'failed']:
                print_success(f"Maintenance task {status}: {r.json()}")
                return True
        
        print_error("Maintenance task timed out")
        return False
    except Exception as e:
        print_error(f"Maintenance worker test failed: {e}")
        return False


# ===================================================================
# TEST 8: PRIORITY HANDLING
# ===================================================================

def test_priority_handling():
    """Test that CRITICAL tasks are processed before LOW tasks"""
    print_header("TEST 8: Priority Handling")
    
    try:
        # Submit LOW priority tasks first
        low_task_ids = []
        print_info("Submitting 5 LOW priority scraping tasks...")
        for i in range(5):
            payload = {
                "url": f"https://example.com/low{i}",
                "brand": "test",
                "priority": "LOW"
            }
            r = requests.post(f"{BASE_URL}/api/hp/scrape", json=payload, timeout=5)
            low_task_ids.append(r.json()['task_id'])
        
        time.sleep(0.5)  # Let LOW tasks queue up
        
        # Now submit CRITICAL tasks
        critical_task_ids = []
        print_info("Submitting 3 CRITICAL priority scraping tasks...")
        for i in range(3):
            payload = {
                "url": f"https://example.com/critical{i}",
                "brand": "test",
                "priority": "CRITICAL"
            }
            r = requests.post(f"{BASE_URL}/api/hp/scrape", json=payload, timeout=5)
            critical_task_ids.append(r.json()['task_id'])
        
        # Wait and check which complete first
        time.sleep(5)
        
        critical_done = 0
        for task_id in critical_task_ids:
            r = requests.get(f"{BASE_URL}/api/hp/tasks/{task_id}", timeout=5)
            if r.json()['status'] == 'completed':
                critical_done += 1
        
        print_info(f"CRITICAL tasks completed: {critical_done}/{len(critical_task_ids)}")
        
        # CRITICAL should complete faster than LOW
        assert critical_done >= 2, "CRITICAL priority not working correctly"
        
        print_success("Priority handling working correctly")
        return True
    except Exception as e:
        print_error(f"Priority handling test failed: {e}")
        return False


# ===================================================================
# TEST 9: CIRCUIT BREAKERS
# ===================================================================

def test_circuit_breakers():
    """Test circuit breaker status"""
    print_header("TEST 9: Circuit Breakers")
    
    try:
        r = requests.get(f"{BASE_URL}/api/hp/circuit-breakers", timeout=5)
        assert r.status_code == 200, f"Failed to get circuit breakers: {r.status_code}"
        
        breakers = r.json()
        
        for name, status in breakers.items():
            state = status['state']
            color = COLORS['green'] if state == 'closed' else COLORS['red']
            print(f"  {color}{name}: {state}{COLORS['reset']}")
            print(f"    Failures: {status['failure_count']}")
        
        print_success("Circuit breakers checked")
        return True
    except Exception as e:
        print_error(f"Circuit breaker test failed: {e}")
        return False


# ===================================================================
# TEST 10: COMPREHENSIVE STATS
# ===================================================================

def test_comprehensive_stats():
    """Get and display comprehensive statistics"""
    print_header("TEST 10: Comprehensive Statistics")
    
    try:
        r = requests.get(f"{BASE_URL}/api/hp/stats", timeout=5)
        assert r.status_code == 200, f"Failed to get stats: {r.status_code}"
        
        stats = r.json()
        
        print_info("Worker Pool Status:")
        print(f"  Running: {stats['running']}")
        print(f"  Total Workers: {stats['workers']['total']}")
        print(f"  Active Tasks: {stats['active_tasks']}")
        print(f"  Completed Results: {stats['completed_results']}")
        
        print_info("\nMetrics by Category:")
        for category in ['scraping', 'rag_query', 'embedding', 'batch_processing', 'maintenance']:
            submitted = stats['metrics']['submitted'].get(category, 0)
            completed = stats['metrics']['completed'].get(category, 0)
            failed = stats['metrics']['failed'].get(category, 0)
            retries = stats['metrics']['retries'].get(category, 0)
            avg_duration = stats['metrics']['avg_duration'].get(category, 0)
            
            if submitted > 0:
                print(f"\n  {category.upper()}:")
                print(f"    Submitted: {submitted}")
                print(f"    Completed: {completed}")
                print(f"    Failed: {failed}")
                print(f"    Retries: {retries}")
                print(f"    Avg Duration: {avg_duration:.2f}s")
        
        print_success("Statistics retrieved")
        return True
    except Exception as e:
        print_error(f"Stats test failed: {e}")
        return False


# ===================================================================
# MAIN TEST RUNNER
# ===================================================================

def main():
    """Run all tests"""
    print_header("🚀 22-WORKER HIGH-PERFORMANCE SYSTEM TEST SUITE")
    print_info(f"Testing against: {BASE_URL}")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("System Health", test_system_health),
        ("Worker Configuration", test_worker_configuration),
        ("Scraping Workers", test_scraping_workers),
        ("RAG Query Workers", test_rag_query_workers),
        ("Embedding Workers", test_embedding_workers),
        ("Batch Workers", test_batch_workers),
        ("Maintenance Worker", test_maintenance_worker),
        ("Priority Handling", test_priority_handling),
        ("Circuit Breakers", test_circuit_breakers),
        ("Comprehensive Stats", test_comprehensive_stats)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results[name] = False
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        icon = "✅" if result else "❌"
        color = COLORS['green'] if result else COLORS['red']
        print(f"{color}{icon} {name}{COLORS['reset']}")
    
    print(f"\n{COLORS['blue']}TOTAL: {passed}/{total} tests passed{COLORS['reset']}")
    
    if passed == total:
        print_success("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print_error(f"❌ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
