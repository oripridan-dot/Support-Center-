#!/usr/bin/env python3
"""
Frontend-Backend Integration Test

Verifies that:
1. Backend API is accessible
2. Frontend can reach backend through proxy
3. All worker endpoints respond correctly
"""

import httpx
import asyncio
import sys

async def test_integration():
    """Run integration tests"""
    
    print("="*70)
    print("FRONTEND-BACKEND INTEGRATION TEST")
    print("="*70)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Direct Backend Access
    print("Test 1: Direct Backend Access (http://localhost:8080)")
    print("-" * 70)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8080/api/workers/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Backend accessible: {data['status']}")
                print(f"  Workers: {data['total_workers']}")
                print(f"  Success Rate: {data['overall_success_rate']*100:.1f}%")
                tests_passed += 1
            else:
                print(f"✗ Backend returned {response.status_code}")
                tests_failed += 1
    except Exception as e:
        print(f"✗ Cannot connect to backend: {e}")
        tests_failed += 1
    
    print()
    
    # Test 2: Frontend Proxy Access
    print("Test 2: Frontend Proxy Access (http://localhost:3001/api)")
    print("-" * 70)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:3001/api/workers/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Frontend proxy working: {data['status']}")
                tests_passed += 1
            else:
                print(f"✗ Proxy returned {response.status_code}")
                tests_failed += 1
    except Exception as e:
        print(f"✗ Cannot connect through proxy: {e}")
        print("  (This is expected if frontend is on port 3000, not 3001)")
        # Try port 3000
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:3000/api/workers/health")
                if response.status_code == 200:
                    print("✓ Frontend proxy working on port 3000")
                    tests_passed += 1
                else:
                    tests_failed += 1
        except:
            tests_failed += 1
    
    print()
    
    # Test 3: Worker Metrics Endpoint
    print("Test 3: Worker Metrics Endpoint")
    print("-" * 70)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8080/api/workers/metrics")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Metrics endpoint accessible")
                print(f"  Categories: {len(data['workers'])}")
                print(f"  Total Processed: {sum(data['processed'].values())}")
                tests_passed += 1
            else:
                print(f"✗ Metrics returned {response.status_code}")
                tests_failed += 1
    except Exception as e:
        print(f"✗ Cannot access metrics: {e}")
        tests_failed += 1
    
    print()
    
    # Test 4: Circuit Breakers
    print("Test 4: Circuit Breaker Status")
    print("-" * 70)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8080/api/workers/circuit-breakers")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Circuit breakers accessible")
                for name, breaker in data.items():
                    print(f"  {name}: {breaker['state']}")
                tests_passed += 1
            else:
                print(f"✗ Circuit breakers returned {response.status_code}")
                tests_failed += 1
    except Exception as e:
        print(f"✗ Cannot access circuit breakers: {e}")
        tests_failed += 1
    
    print()
    
    # Test 5: Frontend Homepage
    print("Test 5: Frontend Homepage")
    print("-" * 70)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try both ports
            for port in [3000, 3001]:
                try:
                    response = await client.get(f"http://localhost:{port}/")
                    if response.status_code == 200:
                        print(f"✓ Frontend accessible on port {port}")
                        tests_passed += 1
                        break
                except:
                    continue
            else:
                print(f"✗ Frontend not accessible on 3000 or 3001")
                tests_failed += 1
    except Exception as e:
        print(f"✗ Cannot access frontend: {e}")
        tests_failed += 1
    
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    
    if tests_failed == 0:
        print()
        print("🎉 All tests passed! Integration is working correctly.")
        print()
        print("You can now access:")
        print("  - Performance Dashboard: http://localhost:3000/performance")
        print("  - API Documentation: http://localhost:8080/docs")
        return True
    else:
        print()
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
