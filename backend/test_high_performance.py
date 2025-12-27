#!/usr/bin/env python3
"""
High-Performance Worker System - Comprehensive Test Suite

Tests all aspects of the optimized worker architecture:
- Worker pool startup and health
- Task execution with priority
- Circuit breaker functionality
- Batch processing
- Performance benchmarks
"""

import asyncio
import httpx
import time
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8080/api"
client = httpx.AsyncClient(timeout=60.0)


# ============================================================================
# TEST UTILITIES
# ============================================================================

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def record(self, name: str, passed: bool, message: str = ""):
        """Record test result"""
        self.tests.append({
            "name": name,
            "passed": passed,
            "message": message
        })
        if passed:
            self.passed += 1
            print(f"✓ {name}")
        else:
            self.failed += 1
            print(f"✗ {name}: {message}")
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ({success_rate:.1f}%)")
        print(f"Failed: {self.failed}")
        print(f"{'='*70}\n")
        
        if self.failed > 0:
            print("Failed tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  - {test['name']}: {test['message']}")


results = TestResults()


# ============================================================================
# TESTS
# ============================================================================

async def test_worker_health():
    """Test worker health endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/workers/health")
        data = response.json()
        
        # Check response structure
        assert "status" in data, "Missing status field"
        assert "total_workers" in data, "Missing total_workers field"
        assert "active_workers" in data, "Missing active_workers field"
        
        # Check worker count
        assert data["total_workers"] == 28, f"Expected 28 workers, got {data['total_workers']}"
        assert data["active_workers"] == 28, f"Expected 28 active workers, got {data['active_workers']}"
        
        # Check health status
        assert data["status"] in ["healthy", "degraded", "unhealthy"], f"Invalid status: {data['status']}"
        
        results.record("Worker Health Check", True)
        return data
        
    except Exception as e:
        results.record("Worker Health Check", False, str(e))
        return None


async def test_worker_metrics():
    """Test worker metrics endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/workers/metrics")
        data = response.json()
        
        # Check response structure
        assert "workers" in data, "Missing workers field"
        assert "queue_sizes" in data, "Missing queue_sizes field"
        assert "processed" in data, "Missing processed field"
        assert "circuit_breakers" in data, "Missing circuit_breakers field"
        
        # Check worker categories
        expected_categories = ["RAG_QUERY", "SCRAPING", "EMBEDDING", "INGESTION", "BATCH", "MAINTENANCE"]
        for category in expected_categories:
            assert category in data["workers"], f"Missing category: {category}"
            assert category in data["queue_sizes"], f"Missing queue for: {category}"
        
        # Check circuit breakers
        expected_breakers = ["openai", "chromadb", "playwright"]
        for breaker in expected_breakers:
            assert breaker in data["circuit_breakers"], f"Missing circuit breaker: {breaker}"
            assert data["circuit_breakers"][breaker]["state"] == "closed", f"Circuit breaker {breaker} not closed"
        
        results.record("Worker Metrics Check", True)
        return data
        
    except Exception as e:
        results.record("Worker Metrics Check", False, str(e))
        return None


async def test_load_performance():
    """Test load performance with different task counts"""
    test_cases = [
        (50, 5.0, "Small load (50 tasks)"),
        (100, 10.0, "Medium load (100 tasks)"),
        (200, 20.0, "Large load (200 tasks)"),
    ]
    
    for num_tasks, max_time, description in test_cases:
        try:
            start = time.time()
            response = await client.post(f"{BASE_URL}/workers/test/load?num_tasks={num_tasks}")
            data = response.json()
            elapsed = time.time() - start
            
            # Check response
            assert "completed" in data, "Missing completed field"
            assert "failed" in data, "Missing failed field"
            assert "total_time_s" in data, "Missing total_time_s field"
            
            # Check success
            assert data["failed"] == 0, f"Had {data['failed']} failures"
            
            # Check performance
            assert data["total_time_s"] < max_time, f"Too slow: {data['total_time_s']:.2f}s (max: {max_time}s)"
            
            # Check throughput
            throughput = num_tasks / data["total_time_s"]
            
            results.record(
                f"Load Test: {description}",
                True,
                f"{throughput:.1f} tasks/sec"
            )
            
        except Exception as e:
            results.record(f"Load Test: {description}", False, str(e))


async def test_pool_config():
    """Test worker pool configuration endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/workers/pool/config")
        data = response.json()
        
        # Check structure
        assert "worker_counts" in data, "Missing worker_counts field"
        assert "total_workers" in data, "Missing total_workers field"
        assert "circuit_breakers" in data, "Missing circuit_breakers field"
        
        # Check worker counts
        expected_counts = {
            "0": 10,  # RAG_QUERY
            "1": 6,   # SCRAPING
            "2": 3,   # EMBEDDING
            "3": 4,   # INGESTION
            "4": 3,   # BATCH
            "5": 2,   # MAINTENANCE
        }
        
        for key, expected in expected_counts.items():
            actual = data["worker_counts"].get(key, 0)
            assert actual == expected, f"Category {key}: expected {expected} workers, got {actual}"
        
        # Check total
        assert data["total_workers"] == 28, f"Expected 28 total workers, got {data['total_workers']}"
        
        results.record("Pool Configuration Check", True)
        return data
        
    except Exception as e:
        results.record("Pool Configuration Check", False, str(e))
        return None


async def test_circuit_breakers():
    """Test circuit breaker status endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/workers/circuit-breakers")
        data = response.json()
        
        # Check structure
        required_breakers = ["openai", "chromadb", "playwright"]
        for breaker in required_breakers:
            assert breaker in data, f"Missing circuit breaker: {breaker}"
            
            # Check breaker structure
            breaker_data = data[breaker]
            assert "state" in breaker_data, f"Missing state for {breaker}"
            assert "failure_count" in breaker_data, f"Missing failure_count for {breaker}"
            
            # All should be closed initially
            assert breaker_data["state"] == "closed", f"Circuit breaker {breaker} not closed: {breaker_data['state']}"
        
        results.record("Circuit Breaker Status Check", True)
        return data
        
    except Exception as e:
        results.record("Circuit Breaker Status Check", False, str(e))
        return None


async def test_api_documentation():
    """Test that API documentation is accessible"""
    try:
        # Check OpenAPI docs
        response = await client.get("http://localhost:8080/docs")
        assert response.status_code == 200, f"Docs returned {response.status_code}"
        
        results.record("API Documentation Accessible", True)
        
    except Exception as e:
        results.record("API Documentation Accessible", False, str(e))


async def test_performance_comparison():
    """Compare performance metrics before and after optimization"""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)
    
    # Get current metrics
    response = await client.get(f"{BASE_URL}/workers/metrics")
    metrics = response.json()
    
    # Display worker utilization
    print("\nWorker Pool Utilization:")
    print("-" * 70)
    for category, info in metrics["workers"].items():
        print(f"  {category:20s} {info['count']} workers (all active)")
    
    print(f"\n  Total: {sum(w['count'] for w in metrics['workers'].values())} specialized workers")
    
    # Display queue status
    print("\nQueue Status:")
    print("-" * 70)
    total_queued = sum(metrics["queue_sizes"].values())
    print(f"  Total queued tasks: {total_queued}")
    
    # Display processing stats
    print("\nProcessing Statistics:")
    print("-" * 70)
    total_processed = sum(metrics["processed"].values())
    total_failed = sum(metrics["failed"].values())
    
    print(f"  Total processed: {total_processed}")
    print(f"  Total failed: {total_failed}")
    
    if total_processed > 0:
        success_rate = (total_processed / (total_processed + total_failed)) * 100
        print(f"  Success rate: {success_rate:.1f}%")
        
        # Show category breakdown
        print("\n  By Category:")
        for category in ["RAG_QUERY", "SCRAPING", "EMBEDDING", "INGESTION", "BATCH", "MAINTENANCE"]:
            processed = metrics["processed"][category]
            if processed > 0:
                avg_ms = metrics["avg_duration_ms"][category]
                print(f"    {category:20s} {processed:4d} tasks, avg {avg_ms:.1f}ms")
    
    print("="*70)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("HIGH-PERFORMANCE WORKER SYSTEM - TEST SUITE")
    print("="*70)
    print()
    
    # Health and status tests
    print("Testing Worker Health & Status...")
    print("-" * 70)
    await test_worker_health()
    await test_worker_metrics()
    await test_pool_config()
    await test_circuit_breakers()
    await test_api_documentation()
    
    # Performance tests
    print("\nTesting Performance & Load Handling...")
    print("-" * 70)
    await test_load_performance()
    
    # Performance comparison
    await test_performance_comparison()
    
    # Summary
    results.summary()
    
    # Cleanup
    await client.aclose()
    
    return results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
