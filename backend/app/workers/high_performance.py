"""
High-Performance Worker System - Production-grade optimization layer

Features:
- Specialized worker pools (Scraping, RAG, Embeddings, Ingestion, Batch)
- 5-tier priority system (Critical → Bulk)
- Circuit breakers for API protection
- Smart retry with exponential backoff
- Connection pooling for ChromaDB and Playwright
- Intelligent batch processing
- Real-time metrics and monitoring
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import IntEnum
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger(__name__)


# ============================================================================
# PRIORITY SYSTEM
# ============================================================================

class TaskPriority(IntEnum):
    """5-tier priority system for optimal resource allocation"""
    CRITICAL = 0   # User-facing queries (RAG, search) - Must be instant
    HIGH = 1       # Important jobs (single scrapes, single embeds)
    NORMAL = 2     # Regular tasks (ingestion, processing)
    LOW = 3        # Background work (maintenance, cleanup)
    BULK = 4       # Batch operations (bulk scraping, bulk embeddings)


class TaskCategory(IntEnum):
    """Task categories for specialized worker pools"""
    RAG_QUERY = 0      # RAG queries (10 dedicated workers)
    SCRAPING = 1       # Web scraping (6 dedicated workers)
    EMBEDDING = 2      # Embedding generation (3 dedicated workers)
    INGESTION = 3      # Document ingestion (4 dedicated workers)
    BATCH = 4          # Batch operations (3 dedicated workers)
    MAINTENANCE = 5    # Cleanup/maintenance (2 dedicated workers)


# ============================================================================
# TASK MODEL
# ============================================================================

@dataclass
class OptimizedTask:
    """Enhanced task with priority, category, and retry logic"""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority = TaskPriority.NORMAL
    category: TaskCategory = TaskCategory.INGESTION
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout: Optional[float] = 300.0  # 5 minutes default
    max_retries: int = 3
    retry_count: int = 0
    retry_delays: List[float] = field(default_factory=lambda: [1, 5, 15])  # Exponential backoff
    
    def __lt__(self, other):
        """Enable comparison for priority queue - lower priority value = higher priority"""
        if not isinstance(other, OptimizedTask):
            return NotImplemented
        return self.priority.value < other.priority.value
    
    def __le__(self, other):
        """Less than or equal"""
        if not isinstance(other, OptimizedTask):
            return NotImplemented
        return self.priority.value <= other.priority.value


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for protecting against cascading failures
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self, 
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
        
        logger.info(f"Initialized circuit breaker: {name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check circuit state
        if self.state == "open":
            # Check if we should try recovery
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
                logger.info(f"Circuit {self.name}: Attempting recovery (half-open)")
                self.state = "half_open"
                self.success_count = 0
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN - service unavailable")
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - update state
            self._on_success()
            return result
            
        except Exception as e:
            # Failure - update state
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit {self.name}: Recovered (closed)")
                self.state = "closed"
                self.success_count = 0
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == "half_open":
            logger.warning(f"Circuit {self.name}: Recovery failed, reopening")
            self.state = "open"
        elif self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit {self.name}: OPENED after {self.failure_count} failures")
            self.state = "open"
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


# ============================================================================
# CONNECTION POOL
# ============================================================================

class ConnectionPool:
    """Generic connection pool for expensive resources"""
    
    def __init__(self, name: str, factory: Callable, max_size: int = 10, min_size: int = 2):
        self.name = name
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.size = 0
        self.initialized = False
        
        logger.info(f"Initialized connection pool: {name} (size: {min_size}-{max_size})")
    
    async def init(self):
        """Initialize pool with minimum connections"""
        if self.initialized:
            return
        
        for _ in range(self.min_size):
            conn = await self._create_connection()
            await self.pool.put(conn)
        
        self.initialized = True
        logger.info(f"Connection pool {self.name} ready with {self.min_size} connections")
    
    async def _create_connection(self) -> Any:
        """Create new connection"""
        self.size += 1
        if asyncio.iscoroutinefunction(self.factory):
            return await self.factory()
        else:
            return self.factory()
    
    async def acquire(self) -> Any:
        """Get connection from pool"""
        if not self.initialized:
            await self.init()
        
        try:
            # Try to get existing connection (non-blocking)
            return self.pool.get_nowait()
        except asyncio.QueueEmpty:
            # Create new connection if under max_size
            if self.size < self.max_size:
                return await self._create_connection()
            # Wait for available connection
            return await self.pool.get()
    
    async def release(self, conn: Any):
        """Return connection to pool"""
        try:
            self.pool.put_nowait(conn)
        except asyncio.QueueFull:
            # Pool full, discard connection
            self.size -= 1
    
    async def close(self):
        """Close all connections"""
        while not self.pool.empty():
            conn = await self.pool.get()
            # Close connection if it has a close method
            if hasattr(conn, 'close'):
                if asyncio.iscoroutinefunction(conn.close):
                    await conn.close()
                else:
                    conn.close()
        
        self.size = 0
        self.initialized = False
        logger.info(f"Connection pool {self.name} closed")


# ============================================================================
# SPECIALIZED WORKER POOL
# ============================================================================

class SpecializedWorkerPool:
    """
    High-performance worker pool with:
    - Multiple specialized sub-pools
    - Priority-based routing
    - Circuit breakers
    - Connection pooling
    - Automatic retry
    - Performance metrics
    """
    
    def __init__(self):
        # Worker pool configuration
        self.worker_config = {
            TaskCategory.RAG_QUERY: 10,      # Most critical - user queries
            TaskCategory.SCRAPING: 6,        # I/O bound
            TaskCategory.EMBEDDING: 3,       # CPU bound (can batch)
            TaskCategory.INGESTION: 4,       # Mixed I/O
            TaskCategory.BATCH: 3,           # Bulk operations
            TaskCategory.MAINTENANCE: 2,     # Background work
        }
        
        # Task queues per category
        self.queues: Dict[TaskCategory, asyncio.PriorityQueue] = {
            category: asyncio.PriorityQueue() for category in TaskCategory
        }
        
        # Workers
        self.workers: Dict[TaskCategory, List[asyncio.Task]] = defaultdict(list)
        self.running = False
        
        # Results storage
        self.results: Dict[str, Dict[str, Any]] = {}
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=20)
        
        # Circuit breakers
        self.circuit_breakers = {
            "openai": CircuitBreaker("openai", failure_threshold=5, recovery_timeout=60),
            "chromadb": CircuitBreaker("chromadb", failure_threshold=3, recovery_timeout=30),
            "playwright": CircuitBreaker("playwright", failure_threshold=5, recovery_timeout=45),
        }
        
        # Connection pools (initialized on startup)
        self.connection_pools: Dict[str, ConnectionPool] = {}
        
        # Metrics
        self.metrics = {
            category: {
                "processed": 0,
                "failed": 0,
                "retries": 0,
                "total_duration_ms": 0,
            } for category in TaskCategory
        }
        
        logger.info("Initialized SpecializedWorkerPool")
    
    async def start(self):
        """Start all worker pools"""
        if self.running:
            logger.warning("Worker pool already running")
            return
        
        self.running = True
        
        # Start workers for each category
        for category, num_workers in self.worker_config.items():
            for worker_id in range(num_workers):
                worker = asyncio.create_task(
                    self._worker(category, worker_id),
                    name=f"{category.name}-{worker_id}"
                )
                self.workers[category].append(worker)
        
        total_workers = sum(len(workers) for workers in self.workers.values())
        logger.info(f"Started {total_workers} specialized workers across {len(TaskCategory)} categories")
    
    async def stop(self):
        """Stop all workers gracefully"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for all workers to finish
        for category_workers in self.workers.values():
            for worker in category_workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
        
        # Close connection pools
        for pool in self.connection_pools.values():
            await pool.close()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("All workers stopped")
    
    async def add_task(self, task: OptimizedTask) -> str:
        """
        Add task to appropriate queue based on category
        
        Args:
            task: OptimizedTask to execute
            
        Returns:
            task_id for tracking
        """
        # Add to category queue - task itself is comparable now
        await self.queues[task.category].put(task)
        
        # Initialize result tracker
        self.results[task.id] = {
            "status": "queued",
            "category": task.category.name,
            "priority": task.priority.name,
            "queued_at": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        logger.debug(f"Task {task.id} queued: category={task.category.name}, priority={task.priority.name}")
        return task.id
    
    async def _worker(self, category: TaskCategory, worker_id: int):
        """
        Specialized worker that processes tasks from category queue
        
        Args:
            category: Category this worker handles
            worker_id: Worker identifier
        """
        worker_name = f"{category.name}-{worker_id}"
        logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Wait for task with timeout - task is directly comparable now
                task = await asyncio.wait_for(
                    self.queues[category].get(),
                    timeout=1.0
                )
                
                logger.debug(f"Worker {worker_name} processing: {task.id}")
                
                # Update status
                self.results[task.id].update({
                    "status": "processing",
                    "started_at": datetime.utcnow().isoformat(),
                    "worker": worker_name
                })
                
                start_time = time.time()
                
                try:
                    # Execute task with timeout
                    result = await asyncio.wait_for(
                        self._execute_task(task),
                        timeout=task.timeout
                    )
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Success
                    self.results[task.id].update({
                        "status": "completed",
                        "result": result,
                        "completed_at": datetime.utcnow().isoformat(),
                        "duration_ms": duration_ms
                    })
                    
                    # Update metrics
                    self.metrics[category]["processed"] += 1
                    self.metrics[category]["total_duration_ms"] += duration_ms
                    
                    logger.info(f"✓ Task {task.id} completed in {duration_ms:.0f}ms")
                    
                except asyncio.TimeoutError:
                    logger.error(f"✗ Task {task.id} timed out after {task.timeout}s")
                    await self._handle_task_failure(task, category, "Timeout exceeded")
                    
                except Exception as e:
                    logger.error(f"✗ Task {task.id} failed: {e}", exc_info=True)
                    await self._handle_task_failure(task, category, str(e))
                
            except asyncio.TimeoutError:
                # No tasks available
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _execute_task(self, task: OptimizedTask) -> Any:
        """
        Execute task function
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        # Check if function is async
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(*task.args, **task.kwargs)
        else:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                functools.partial(task.func, *task.args, **task.kwargs)
            )
    
    async def _handle_task_failure(self, task: OptimizedTask, category: TaskCategory, error: str):
        """
        Handle task failure with retry logic
        
        Args:
            task: Failed task
            category: Task category
            error: Error message
        """
        task.retry_count += 1
        
        # Check if we should retry
        if task.retry_count <= task.max_retries:
            # Calculate retry delay (exponential backoff)
            delay = task.retry_delays[min(task.retry_count - 1, len(task.retry_delays) - 1)]
            
            logger.info(f"Retrying task {task.id} in {delay}s (attempt {task.retry_count}/{task.max_retries})")
            
            # Update result
            self.results[task.id].update({
                "status": "retrying",
                "retry_count": task.retry_count,
                "last_error": error,
                "retry_at": (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
            })
            
            # Re-queue after delay
            await asyncio.sleep(delay)
            await self.queues[category].put(task)
            
            # Update metrics
            self.metrics[category]["retries"] += 1
        else:
            # Max retries exceeded
            logger.error(f"Task {task.id} failed permanently after {task.retry_count} attempts")
            
            self.results[task.id].update({
                "status": "failed",
                "error": error,
                "retry_count": task.retry_count,
                "failed_at": datetime.utcnow().isoformat()
            })
            
            # Update metrics
            self.metrics[category]["failed"] += 1
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        return self.results.get(task_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        return {
            "workers": {
                category.name: {
                    "count": len(self.workers[category]),
                    "active": sum(1 for w in self.workers[category] if not w.done())
                } for category in TaskCategory
            },
            "queue_sizes": {
                category.name: self.queues[category].qsize() 
                for category in TaskCategory
            },
            "processed": {
                category.name: self.metrics[category]["processed"]
                for category in TaskCategory
            },
            "failed": {
                category.name: self.metrics[category]["failed"]
                for category in TaskCategory
            },
            "retries": {
                category.name: self.metrics[category]["retries"]
                for category in TaskCategory
            },
            "avg_duration_ms": {
                category.name: (
                    self.metrics[category]["total_duration_ms"] / self.metrics[category]["processed"]
                    if self.metrics[category]["processed"] > 0 else 0
                ) for category in TaskCategory
            },
            "success_rate": {
                category.name: (
                    self.metrics[category]["processed"] / 
                    (self.metrics[category]["processed"] + self.metrics[category]["failed"])
                    if (self.metrics[category]["processed"] + self.metrics[category]["failed"]) > 0
                    else 1.0
                ) for category in TaskCategory
            },
            "circuit_breakers": {
                name: breaker.get_state() 
                for name, breaker in self.circuit_breakers.items()
            }
        }


# ============================================================================
# BATCH PROCESSOR
# ============================================================================

class BatchProcessor:
    """Intelligent batch processing for bulk operations"""
    
    def __init__(self, worker_pool: SpecializedWorkerPool):
        self.worker_pool = worker_pool
        logger.info("Initialized BatchProcessor")
    
    async def batch_scrape(
        self, 
        urls: List[str], 
        brand: str,
        batch_size: int = 10
    ) -> List[str]:
        """
        Batch scrape multiple URLs in parallel
        
        Args:
            urls: List of URLs to scrape
            brand: Brand name
            batch_size: Number of URLs to scrape in parallel
            
        Returns:
            List of task IDs
        """
        task_ids = []
        
        # Import here to avoid circular dependency
        from app.workers.scraper import scrape_url
        
        # Process in batches
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            for url in batch:
                task = OptimizedTask(
                    id=f"scrape_{brand}_{i}_{url[:20]}",
                    func=scrape_url,
                    args=(url, brand),
                    kwargs={},
                    priority=TaskPriority.BULK,
                    category=TaskCategory.SCRAPING,
                    timeout=180.0
                )
                task_id = await self.worker_pool.add_task(task)
                task_ids.append(task_id)
            
            # Small delay between batches to avoid overwhelming
            await asyncio.sleep(0.1)
        
        logger.info(f"Queued {len(urls)} URLs for scraping in {len(task_ids)} tasks")
        return task_ids
    
    async def batch_embed(
        self,
        texts: List[str],
        batch_size: int = 50
    ) -> List[str]:
        """
        Batch generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to embed per batch
            
        Returns:
            List of task IDs
        """
        task_ids = []
        
        # Import here to avoid circular dependency
        from app.services.llm import generate_embeddings
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            task = OptimizedTask(
                id=f"embed_batch_{i}_{len(batch)}",
                func=generate_embeddings,
                args=(batch,),
                kwargs={},
                priority=TaskPriority.BULK,
                category=TaskCategory.EMBEDDING,
                timeout=120.0
            )
            task_id = await self.worker_pool.add_task(task)
            task_ids.append(task_id)
        
        logger.info(f"Queued {len(texts)} texts for embedding in {len(task_ids)} batches")
        return task_ids


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

# Global worker pool instance
worker_pool = SpecializedWorkerPool()

# Global batch processor
batch_processor = BatchProcessor(worker_pool)

# Export circuit breakers for use in services
openai_breaker = worker_pool.circuit_breakers["openai"]
chromadb_breaker = worker_pool.circuit_breakers["chromadb"]
playwright_breaker = worker_pool.circuit_breakers["playwright"]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def submit_task(
    task_id: str,
    func: Callable,
    priority: TaskPriority = TaskPriority.NORMAL,
    category: TaskCategory = TaskCategory.INGESTION,
    *args,
    **kwargs
) -> str:
    """
    Convenient helper to submit a task
    
    Args:
        task_id: Unique task identifier
        func: Function to execute
        priority: Task priority
        category: Task category
        *args, **kwargs: Function arguments
        
    Returns:
        task_id
    """
    task = OptimizedTask(
        id=task_id,
        func=func,
        args=args,
        kwargs=kwargs,
        priority=priority,
        category=category
    )
    return await worker_pool.add_task(task)


async def get_task_result(task_id: str, timeout: float = 300.0) -> Any:
    """
    Wait for task completion and get result
    
    Args:
        task_id: Task identifier
        timeout: Maximum wait time in seconds
        
    Returns:
        Task result
        
    Raises:
        TimeoutError: If task doesn't complete in time
        Exception: If task failed
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = worker_pool.get_task_status(task_id)
        
        if not status:
            raise Exception(f"Task {task_id} not found")
        
        if status["status"] == "completed":
            return status.get("result")
        elif status["status"] == "failed":
            raise Exception(f"Task failed: {status.get('error')}")
        
        await asyncio.sleep(0.1)
    
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


logger.info("High-performance worker system loaded")
