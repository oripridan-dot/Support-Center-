"""
High-Performance Worker Pool System
22 Specialized Workers with Circuit Breakers, Retry Logic, and Priority Queues

Worker Distribution:
- Scraping: 6 workers
- RAG Query: 10 workers (CRITICAL priority)
- Embedding: 3 workers
- Batch Processing: 2 workers
- Maintenance: 1 worker
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Optional, Any, List
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels (lower number = higher priority)"""
    CRITICAL = 1  # User-facing queries - must be fast
    HIGH = 2      # Important operations
    NORMAL = 5    # Standard tasks
    LOW = 8       # Background work
    BULK = 10     # Large batch jobs


class TaskCategory(Enum):
    """Task categories for specialized worker pools"""
    SCRAPING = "scraping"
    RAG_QUERY = "rag_query"
    EMBEDDING = "embedding"
    BATCH_PROCESSING = "batch_processing"
    MAINTENANCE = "maintenance"


@dataclass
class OptimizedTask:
    """Task with priority and metadata"""
    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    category: TaskCategory = TaskCategory.SCRAPING
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __lt__(self, other):
        """For priority queue comparison"""
        return self.priority.value < other.priority.value


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: str  # 'completed', 'failed', 'timeout', 'cancelled'
    result: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    retries: int = 0
    completed_at: Optional[datetime] = None


class CircuitBreaker:
    """Circuit breaker for API protection"""
    
    def __init__(self, name: str, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        
    def record_success(self):
        """Record successful call"""
        if self.state == "half_open":
            logger.info(f"Circuit breaker [{self.name}] recovered - closing")
            self.state = "closed"
            self.failure_count = 0
            
    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker [{self.name}] opened - "
                f"{self.failure_count} failures"
            )
            self.state = "open"
            
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    logger.info(f"Circuit breaker [{self.name}] trying half-open")
                    self.state = "half_open"
                    return True
            return False
            
        # half_open - allow one try
        return True
    
    def get_status(self) -> dict:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class WorkerPool:
    """High-performance worker pool with specialized workers"""
    
    def __init__(self):
        # Worker configuration: category -> number of workers
        self.worker_config = {
            TaskCategory.SCRAPING: 6,
            TaskCategory.RAG_QUERY: 10,
            TaskCategory.EMBEDDING: 3,
            TaskCategory.BATCH_PROCESSING: 2,
            TaskCategory.MAINTENANCE: 1
        }
        
        # Priority queues for each category
        self.queues: Dict[TaskCategory, asyncio.PriorityQueue] = {
            category: asyncio.PriorityQueue()
            for category in TaskCategory
        }
        
        # Thread executor for blocking operations
        total_workers = sum(self.worker_config.values())
        self.executor = ThreadPoolExecutor(max_workers=total_workers)
        
        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Track active pipeline workers (not in thread pool)
        self._active_workers_count = 0
        
        # Results storage
        self.results: Dict[str, TaskResult] = {}
        
        # Circuit breakers for external services
        self.circuit_breakers = {
            "openai": CircuitBreaker("OpenAI", failure_threshold=5, timeout_seconds=60),
            "chromadb": CircuitBreaker("ChromaDB", failure_threshold=3, timeout_seconds=30),
            "playwright": CircuitBreaker("Playwright", failure_threshold=5, timeout_seconds=45)
        }
        
        # Metrics
        self.metrics = {
            "tasks_submitted": defaultdict(int),
            "tasks_completed": defaultdict(int),
            "tasks_failed": defaultdict(int),
            "total_duration": defaultdict(float),
            "retries": defaultdict(int)
        }
        
        # Task tracking
        self.active_tasks: Dict[str, OptimizedTask] = {}
        
    async def add_task(self, task: OptimizedTask) -> str:
        """Add a task to the appropriate queue"""
        self.active_tasks[task.id] = task
        self.metrics["tasks_submitted"][task.category.value] += 1
        
        await self.queues[task.category].put((task.priority.value, task))
        
        logger.info(
            f"Task [{task.id}] queued - "
            f"Category: {task.category.value}, "
            f"Priority: {task.priority.name}, "
            f"Queue size: {self.queues[task.category].qsize()}"
        )
        
        return task.id
    
    async def _execute_with_retry(self, task: OptimizedTask) -> TaskResult:
        """Execute task with retry logic"""
        start_time = time.time()
        retries = 0
        last_error = None
        
        for attempt in range(task.max_retries):
            try:
                # Check circuit breakers for external services
                if task.category == TaskCategory.RAG_QUERY:
                    if not self.circuit_breakers["openai"].can_execute():
                        raise Exception("OpenAI circuit breaker open")
                    if not self.circuit_breakers["chromadb"].can_execute():
                        raise Exception("ChromaDB circuit breaker open")
                elif task.category == TaskCategory.SCRAPING:
                    if not self.circuit_breakers["playwright"].can_execute():
                        raise Exception("Playwright circuit breaker open")
                
                # Execute task in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        task.func,
                        *task.args,
                        **task.kwargs
                    ),
                    timeout=task.timeout_seconds
                )
                
                # Success - update circuit breakers
                if task.category == TaskCategory.RAG_QUERY:
                    self.circuit_breakers["openai"].record_success()
                    self.circuit_breakers["chromadb"].record_success()
                elif task.category == TaskCategory.SCRAPING:
                    self.circuit_breakers["playwright"].record_success()
                
                duration = time.time() - start_time
                return TaskResult(
                    task_id=task.id,
                    status="completed",
                    result=result,
                    duration_seconds=duration,
                    retries=retries,
                    completed_at=datetime.utcnow()
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Task [{task.id}] timed out after {task.timeout_seconds}s")
                duration = time.time() - start_time
                return TaskResult(
                    task_id=task.id,
                    status="timeout",
                    error=f"Timeout after {task.timeout_seconds}s",
                    duration_seconds=duration,
                    retries=retries,
                    completed_at=datetime.utcnow()
                )
                
            except Exception as e:
                retries += 1
                last_error = str(e)
                
                # Update circuit breakers on failure
                if task.category == TaskCategory.RAG_QUERY:
                    if "OpenAI" in str(e) or "openai" in str(e):
                        self.circuit_breakers["openai"].record_failure()
                    if "Chroma" in str(e) or "chroma" in str(e):
                        self.circuit_breakers["chromadb"].record_failure()
                elif task.category == TaskCategory.SCRAPING:
                    if "Playwright" in str(e) or "browser" in str(e):
                        self.circuit_breakers["playwright"].record_failure()
                
                if attempt < task.max_retries - 1:
                    # Exponential backoff
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(
                        f"Task [{task.id}] failed (attempt {attempt + 1}/{task.max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    self.metrics["retries"][task.category.value] += 1
                else:
                    logger.error(f"Task [{task.id}] failed after {task.max_retries} attempts: {e}")
        
        # All retries exhausted
        duration = time.time() - start_time
        return TaskResult(
            task_id=task.id,
            status="failed",
            error=last_error,
            duration_seconds=duration,
            retries=retries,
            completed_at=datetime.utcnow()
        )
    
    async def _worker(self, category: TaskCategory, worker_id: int):
        """Worker coroutine for processing tasks"""
        worker_name = f"{category.value.upper()}-{worker_id}"
        logger.info(f"Worker [{worker_name}] started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                priority, task = await asyncio.wait_for(
                    self.queues[category].get(),
                    timeout=1.0
                )
                
                logger.info(
                    f"Worker [{worker_name}] processing task [{task.id}] "
                    f"(Priority: {task.priority.name})"
                )
                
                # Execute task with retry logic
                result = await self._execute_with_retry(task)
                
                # Store result
                self.results[task.id] = result
                
                # Update metrics
                if result.status == "completed":
                    self.metrics["tasks_completed"][category.value] += 1
                    logger.info(
                        f"Worker [{worker_name}] ✅ Task [{task.id}] completed in "
                        f"{result.duration_seconds:.2f}s (retries: {result.retries})"
                    )
                else:
                    self.metrics["tasks_failed"][category.value] += 1
                    logger.error(
                        f"Worker [{worker_name}] ❌ Task [{task.id}] {result.status}: "
                        f"{result.error}"
                    )
                
                self.metrics["total_duration"][category.value] += result.duration_seconds
                
                # Remove from active tasks
                self.active_tasks.pop(task.id, None)
                
            except asyncio.TimeoutError:
                # No tasks in queue - continue waiting
                continue
            except Exception as e:
                logger.error(f"Worker [{worker_name}] error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def start(self):
        """Start all worker pools"""
        if self.running:
            logger.warning("Worker pool already running")
            return
        
        self.running = True
        
        logger.info("=" * 70)
        logger.info("🚀 STARTING HIGH-PERFORMANCE WORKER POOL")
        logger.info("=" * 70)
        
        # Start workers for each category
        for category, num_workers in self.worker_config.items():
            for worker_id in range(num_workers):
                worker_task = asyncio.create_task(
                    self._worker(category, worker_id)
                )
                self.workers.append(worker_task)
            
            logger.info(f"  • {category.value.upper()}: {num_workers} workers")
        
        logger.info(f"  • TOTAL: {len(self.workers)} workers")
        logger.info("=" * 70)
        logger.info("✅ Worker pool ready")
        logger.info("")
    
    async def stop(self):
        """Stop all workers"""
        logger.info("Stopping worker pool...")
        self.running = False
        
        # Wait for all workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("🛑 Worker pool stopped")
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result for a completed task"""
        return self.results.get(task_id)
    
    def get_task_status(self, task_id: str) -> dict:
        """Get status of a task"""
        # Check if task is still active
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "processing",
                "category": task.category.value,
                "priority": task.priority.name,
                "created_at": task.created_at.isoformat()
            }
        
        # Check if task is completed
        if task_id in self.results:
            result = self.results[task_id]
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "duration_seconds": result.duration_seconds,
                "retries": result.retries,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None
            }
        
        return {
            "task_id": task_id,
            "status": "not_found"
        }
    
    def get_stats(self) -> dict:
        """Get worker pool statistics"""
        # Include pipeline active workers in total active count
        pipeline_active = getattr(self, '_active_workers_count', 0)
        
        stats = {
            "running": self.running,
            "workers": {
                "total": len(self.workers),
                "by_category": {
                    category.value: count
                    for category, count in self.worker_config.items()
                }
            },
            "queues": {
                category.value: self.queues[category].qsize()
                for category in TaskCategory
            },
            "active_tasks": len(self.active_tasks) + pipeline_active,  # Pool tasks + pipeline workers
            "completed_results": len(self.results),
            "metrics": {
                "submitted": dict(self.metrics["tasks_submitted"]),
                "completed": dict(self.metrics["tasks_completed"]),
                "failed": dict(self.metrics["tasks_failed"]),
                "retries": dict(self.metrics["retries"]),
                "avg_duration": {
                    category: (
                        self.metrics["total_duration"][category] / 
                        self.metrics["tasks_completed"][category]
                    ) if self.metrics["tasks_completed"][category] > 0 else 0
                    for category in [c.value for c in TaskCategory]
                }
            },
            "circuit_breakers": {
                name: breaker.get_status()
                for name, breaker in self.circuit_breakers.items()
            }
        }
        
        return stats
    
    def get_health(self) -> dict:
        """Get health status"""
        # Check if workers are healthy
        healthy_workers = sum(1 for w in self.workers if not w.done())
        total_workers = len(self.workers)
        
        # Check circuit breakers
        breakers_ok = all(
            breaker.state != "open"
            for breaker in self.circuit_breakers.values()
        )
        
        # Calculate health score
        worker_health = healthy_workers / total_workers if total_workers > 0 else 0
        
        is_healthy = (
            self.running and
            worker_health >= 0.8 and  # At least 80% workers running
            breakers_ok
        )
        
        return {
            "healthy": is_healthy,
            "running": self.running,
            "workers": {
                "healthy": healthy_workers,
                "total": total_workers,
                "health_percentage": round(worker_health * 100, 1)
            },
            "circuit_breakers": {
                name: breaker.state
                for name, breaker in self.circuit_breakers.items()
            }
        }


# Global instance
hp_worker_pool = WorkerPool()
